import subprocess
import datetime
import time
# import matplotlib.pyplot as plt # used below for generating visualizations

class TaskTimerSh:
    """class to launch the task-timer.sh script as a subprocess"""
    def __init__(self, no_launch=False, log_dir="./logs"):

        _date = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')
        self.activity_log_file=f"{log_dir}/{_date}_activity_log.txt"

        if no_launch:
            return
        
        try:
            # launch the task_timer_script as a subprocess
            self.process = subprocess.Popen(["./task-timer.sh"])
            time.sleep(.4)

            # wait for user input to terminate
            input("Press enter to exit and terminate the app...")
            self.terminate()

        except Exception as e:
            print(f"error launching process: {e}")
            pass



    def terminate(self):
        """gracefully terminate the process"""

        # terminate the subprocess gracefully
        self.process.terminate()

        # wait for the subprocess to exit
        self.process.wait()

        time.sleep(2)

        # compress the activity log file
        self.generate_visualizations(filepath=self.activity_log_file)


    def _format_duration(self, seconds):
        """format an integer as a duration 00:00:00"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"



    def _parse_duration(self, duration):
        """Parse a duration string (e.g., '00:00:34') into a total seconds"""
        duration_obj = datetime.datetime.strptime(duration, '%H:%M:%S')
        total_seconds = duration_obj.hour * 3600 + duration_obj.minute * 60 + duration_obj.second
        return total_seconds



    def _group_short_activities_with_previous_long_one(self, activity_log_data):
        """
        Parameters
        -----------
        activity_log_data : list
            a list of activity log objects
        """
        # {'apps': {'Safari': 38}, 'start_time': datetime.datetime(2024, 11, 25, 9, 20, 44), 'end_time': datetime.datetime(2024, 11, 25, 9, 21, 22), 'duration_seconds': 38}

        min_duration_for_group_start = 60
        groups = []
        current_group = []
        
        for idx, activity_obj in enumerate(activity_log_data):

            activity = list(activity_obj['apps'].keys())[0]

            if len(current_group) == 0:
                current_group.append(activity_obj)
            elif activity_obj['duration_seconds'] > min_duration_for_group_start:
                groups.append(current_group)
                current_group = [activity_obj]
            elif activity == "Idle" or "Idle" in activity_log_data[idx - 1]['apps'].keys():
                groups.append(current_group)
                current_group = [activity_obj]
            else:
                current_group.append(activity_obj)

        groups.append(current_group)

        return self._merge_groups_of_activity_logs(groups)



    def _group_consecutive_activities_with_previous_line(self, activity_log_data):
        """
        Parameters
        -----------
        activity_log_data : list
            a list of activity log objects
        """

        # extract the apps from each line into a sorted list of lists so they are uniform
        sorted_app_names = [sorted(list(log["apps"].keys())) for log in activity_log_data]

        # loop through all of the activity log data and group consecutive lines with the same apps together
        groups = []
        current_group = []
        for i in range(len(activity_log_data)):
            if i == 0:
                current_group.append(activity_log_data[i])
            elif sorted_app_names[i] == sorted_app_names[i - 1]:
                current_group.append(activity_log_data[i])
            else:
                groups.append(current_group)
                current_group = []
                current_group.append(activity_log_data[i])

        groups.append(current_group)

        return self._merge_groups_of_activity_logs(groups)



    def _group_activities_by_hour(self, activity_log_data):
        """
        Parameters
        -----------
        activity_log_data : list
            a list of activity log objects
        """

        group_start_activity = None
        groups = []
        current_group = []
        
        for activity_obj in activity_log_data:
            # {'apps': {'Safari': 38}, 'start_time': datetime.datetime(2024, 11, 25, 9, 20, 44), 'end_time': datetime.datetime(2024, 11, 25, 9, 21, 22), 'duration_seconds': 38}

            if len(current_group) == 0:
                group_start_activity = activity_obj
                current_group.append(activity_obj)

            elif activity_obj['start_time'].hour != group_start_activity['start_time'].hour:
                groups.append(current_group)
                group_start_activity = activity_obj
                current_group = [activity_obj]
            else:
                current_group.append(activity_obj)
            
        groups.append(current_group)

        # return groups
        return self._merge_groups_of_activity_logs(groups)




    def _merge_groups_of_activity_logs(self, list_of_lists_of_activity_entries):
        groups = list_of_lists_of_activity_entries

        # for each group
        merged_group_data = []
        for group in groups:
            first_entry_in_group = True

            # loop through each line in the group
            for entry in group:

                if first_entry_in_group:
                    # initialize the values as the first line in the group
                    start_time = group[0]["start_time"]
                    end_time = group[0]["end_time"]
                    duration_seconds = group[0]["duration_seconds"]
                    apps = group[0]["apps"]
                    first_entry_in_group = False
                    continue

                # update the end time
                end_time = entry["end_time"]
                # add this lines duration to the total duration
                duration_seconds += entry["duration_seconds"]

                # for each app in the line
                for app_name in entry["apps"].keys():
                    apps[app_name] = apps.get(app_name, 0) + entry["apps"][app_name]

            merged_group_data.append({
                "start_time": start_time,
                "end_time": end_time,
                "apps": apps,
                "duration_seconds": sum([v for v in apps.values()])
            })

        return merged_group_data



    def parse_activity_log_line(self, activity_log_line):
        """
        parse a line of the activity log into an object

        Parameters
        -----------
        activity_log_line : string
            a string containing a single line of the activity log

            - `2024-11-25 09:21:22 - 2024-11-25 09:21:23: Visual Studio Code(00:00:01)`
            - `2024-11-21 09:39:00 - 2024-11-21 09:57:07 - 00:18:07: Visual Studio Code(00:04:20), Terminal(00:02:08)`

        Returns
        -----------
        object representing the line of data
            - `{'apps': {'Safari': 38}, 'start_time': datetime.datetime(2024, 11, 25, 9, 20, 44), 'end_time': datetime.datetime(2024, 11, 25, 9, 21, 22), 'duration_seconds': 38}`

        """
        line_data = {"apps": {}}
        raw_time_data, raw_app_data = activity_log_line.split(": ")

        # process the app data from the line
        raw_apps = raw_app_data.split(", ")
        for app_data in raw_apps:
            app_name, app_duration = app_data.split("(")
            app_duration_str = app_duration.replace(")", "")
            line_data["apps"][app_name] = self._parse_duration(app_duration_str)

        # process the time data from the line
        raw_time_data_parts = raw_time_data.split(" - ")
        if len(raw_time_data_parts) == 3:
            start_time_str, end_time_str, duration_str = raw_time_data_parts
            total_duration = self._parse_duration(duration_str)
        if len(raw_time_data_parts) == 2:
            start_time_str, end_time_str = raw_time_data_parts
            total_duration = line_data["apps"][app_name]

        # convert the time data to datetime objects
        line_data["start_time"] = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        line_data["end_time"] = datetime.datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        line_data["duration_seconds"] = total_duration

        return line_data

        # print(parse_activity_log_line("2024-11-25 09:21:22 - 2024-11-25 09:21:23: Visual Studio Code(00:00:01)"))
        # print(parse_activity_log_line("2024-11-21 09:39:00 - 2024-11-21 09:57:07 - 00:18:07: Visual Studio Code(00:04:20), Terminal(00:02:08)"))



    def parse_log_lines(self, log_lines_input, input_type="string"):
        """process log data into a list of activity objects"""
        if input_type == "path":
            with open(log_lines_input, 'r') as f:
                log_lines = f.readlines()
        elif input_type == "string":
            log_lines = log_lines_input.split("\n")
        elif input_type == "list":
            pass

        activities = []
        for line in log_lines:
            line = line.strip()
            if not line:
                continue
            activities.append(self.parse_activity_log_line(line))

        # print("activities[0]: ", activities[0])
        # print("activities[1]: ", activities[1])
        # print("activities[2]: ", activities[2])

        return activities



    def _generate_visualizations(self, activities_data, outfile=None):
        print("generating visualizations...")
        import matplotlib
        # use the 'agg' backend for non-gui rendering
        matplotlib.use('Agg') # or use plt.close() to close the figure after saving the file
        import matplotlib.pyplot as plt

        # create a new color object for generating app colors
        colors = Colors(plt)

        # set the bars to be full width
        full_width_bars = True
        markers_at_start = True

        # calculate total duration of all activities
        total_duration = sum(activity["duration_seconds"] for activity in activities_data)

        MIN_DURATION_FOR_LABEL = total_duration / 150
        MIN_DURATION_FOR_LEGEND_ENTRY = 65

        # prepare labels and positions of labels for x axis
        activity_labels = []
        bar_centers = []
        bar_start_positions = [0]
        cleaned_bar_start_positions = []
        cleaned_bar_centers = []
        cleaned_durations = []
        cleaned_activity_labels = []

        # dictionary to store handles for unique app names and durations
        total_data = {}
        # dictionary to store handles for unique app names and bar segments
        legend_handles = {}

        # extract the figure and axis from matplotlib
        fig, ax = plt.subplots(figsize=(20, 6))

        # loop through each activity
        for i, activity in enumerate(activities_data):

            # set the bar width to the duration of the activity, or 1 for them to be equal
            duration = activity["duration_seconds"]
            bar_width = duration
            # bar_width = 1

            # set the label to the start time of the row
            activity_label = activity["start_time"].time()
            activity_labels.append(activity_label)

            # define the bottom of the current segment of the current bar
            bottom_of_segment = 0

            # define padding add it to the bar width for whitespace
            bar_padding = bar_width / 10
            bar_area_width = bar_width + (bar_padding * 2)

            # if you want the bars to fill the entire space, remove the padding
            if full_width_bars:
                bar_area_width = bar_width

            # define the start position of each bar as the last bars start plus the width
            if i != (len(activities_data) - 1):
                bar_start_position = bar_start_positions[-1] + bar_area_width
                bar_start_positions.append(bar_start_position)

            # location of the label is the starting position plus half of the width of the bar
            bar_center = bar_start_positions[i] + (bar_area_width / 2)
            bar_centers.append(bar_center)

            # to avoid crowding, only show labels for activities longer than a certain duration
            if markers_at_start:
                if i == 0 or i == len(activities_data) - 1 or bar_start_positions[i] - cleaned_bar_start_positions[-1] > MIN_DURATION_FOR_LABEL:
                    duration_mins = duration / 60
                    cleaned_bar_start_positions.append(bar_start_positions[i])
                    cleaned_bar_centers.append(bar_center)
                    cleaned_activity_labels.append(activity_label)
                    cleaned_durations.append(duration_mins)

            elif i == 0 or i == len(activities_data) - 1 or bar_center - cleaned_bar_centers[-1] > MIN_DURATION_FOR_LABEL:
                duration_mins = duration / 60
                cleaned_bar_start_positions.append(bar_start_positions[i])
                cleaned_bar_centers.append(bar_center)
                cleaned_activity_labels.append(activity_label)
                cleaned_durations.append(duration_mins)


            # extract the app names and sort them by duration
            app_items = list(activity['apps'].items())
            app_items.sort(key=lambda x: x[1], reverse=True)

            # iterate through each app in the row
            for app_name, duration in app_items:
                # add the duration to the total data for the app
                total_data[app_name] = total_data.get(app_name, 0) + duration

                # deemphasize any short activities from the visualization
                if app_name.lower() in ["idle", "loginwindow"]:
                    duration = (total_duration / len(activities_data)) / 3

                # convert the duration to minutes
                duration = duration / 60

                # get the color associated with the app name
                color = colors.get_color(app_name.lower())

                # create the stack for the bar where each app in the row is a segment
                bar = ax.bar(bar_centers[i], duration, bottom=bottom_of_segment, label=app_name, color=color, align='center', width=bar_width)
                bottom_of_segment += duration

                # store the handle for the legend if not already stored
                if app_name not in legend_handles:
                    # only store the first bar segment for the app
                    legend_handles[app_name] = bar[0]

                # todo: rework this for this instance - alternatively, define the bar using the start position and align edge
                # ax.bar(bar_start_positions[i], bar_height, width=bar_width, align="edge", label=activity["name"])

        # if the bar width is 1, we need to acccount for the new width of the plot, 1 unit per bar
        if bar_width == 1:
            total_duration = len(activities_data)


        # if you want to manually set the margins and space, you can define the low and high value for the x axis with a little margin
        if full_width_bars:
            # set x-axis limits to remove whitespace
            margin = total_duration / 100
            ax.set_xlim(-margin, total_duration + margin)
            # this sets x-axis limits to a range between 0 and 1
            # ax.set_xlim(0, 1)


        # create custom legend labels with totals
        sorted_total_data = sorted(total_data.items(), key=lambda x: x[1], reverse=True)

        # sort handles and labels by duration
        sorted_handles = []
        sorted_labels = []
        for app_name, duration in sorted_total_data:
            if(duration > MIN_DURATION_FOR_LEGEND_ENTRY):
                sorted_labels.append(f"{self._format_duration(duration)} - {app_name}({f'{((duration / total_duration) * 100):.1f}%'})")
                sorted_handles.append(legend_handles[app_name])



        # set the labels
        if markers_at_start:
            plt.xticks(cleaned_bar_start_positions, cleaned_activity_labels)
        else:
            plt.xticks(cleaned_bar_centers, cleaned_activity_labels)

        # turn the labels sideways
        plt.xticks(rotation=90)

        # add legend
        ax.legend()
        # ax.legend(handles=sorted_handles, labels=sorted_labels, loc="upper left", prop={'size': 8})
        # ax.legend(handles=sorted_handles, labels=sorted_labels, loc=(.1, .42), prop={'size': 8})
        ax.legend(
            handles=sorted_handles, 
            labels=sorted_labels,
            loc="upper left", 
            bbox_to_anchor=(.1, .97),
            # bbox_to_anchor=(.935, 1.04), # right side
            borderaxespad=0, 
            prop={'size': 8},
            title=f"Activity Hours({self._format_duration(total_duration)})"
        )

        # # annotate the bars with percentages
        # for i, duration in enumerate(cleaned_durations):
        #     if duration > MIN_DURATION_FOR_LABEL:
        #         percent = (duration / total_duration) * 100
        #         plt.text(cleaned_bar_centers[i], duration - 50, f'{percent:.1f}%', ha='center')


        # customize the plot and legend
        plt.xlabel("Activity")
        plt.ylabel("Duration (mins)")
        plt.title("App Usage by Activity")
        # plt.legend(handles=list(total_data.keys()), loc="upper left", prop={'size': 8})
        plt.tight_layout(pad=0.1)

        if not outfile:
            plt.show()
        else:
            plt.savefig(outfile)

        # for app_name in total_data.keys():
        #     print(f'"{app_name.lower()}": {colors.get_color(app_name)}')



    def generate_visualizations(self, filepath=None, string_data=None, outfile=None):
        if not filepath and not string_data:
            filepath = self.activity_log_file
            activities_data = self.parse_log_lines(filepath, "path")

        elif string_data:
            activities_data = self.parse_log_lines(string_data, "string")

        elif filepath:
            activities_data = self.parse_log_lines(filepath, "path")
        
        result = self._group_short_activities_with_previous_long_one(activities_data)
        result = self._group_consecutive_activities_with_previous_line(result)

        if not outfile:
            outfile_path_parts = filepath.split("/")
            outfile_name = "".join(outfile_path_parts[-1].split(".")[:-1]) + ".png"
            outfile_path = "/".join([*outfile_path_parts[:-1], outfile_name])
        else:
            outfile_path = outfile

        self._generate_visualizations(result, outfile_path)



class Colors:
    def __init__(self, plt):

        # define a dictionary to store colors for each app
        self.app_colors = {}

        # choose a colormap with 20 colors
        self.color_map = plt.cm.tab20.colors
        self.color_index = 2

        # define a dictionary for any preset colors
        self.preset_colors = {
            # lighter should be more productive

            "idle": (0.86, 0.86, 0.86),

            "screencaptureui": (0.75, 0.75, 0.75),
            "archive utility": (0.65, 0.65, 0.65),
            "terminal": (0.55, 0.55, 0.55),

            "loginwindow": (0.91, 0.91, 0.91),      
            "coreautha.bundle": (0.91, 0.91, 0.91),
            "keyboard maestro engine": (0.91, 0.91, 0.91),
            "bettermouse": (0.91, 0.91, 0.91),
            "controlcenter": (0.91, 0.91, 0.91),
            "usernotificationcenter": (0.91, 0.91, 0.91),
            "notificationcenter": (0.91, 0.91, 0.91),

            "finder": (0.314, 0.369, 0.831),
            "preview": (0.859, 0.902, 0.267),
            "calculator": (0.929, 0.706, 0.208),

            "microsoft outlook": (0, 0.624, 0.91),
            "microsoft edge": (0.035, 0.486, 0.71),
            "onedrive": (0.0, 0.47, 0.86),
            "microsoft excel": (0.1725, 0.6274, 0.1725),

            "affinity designer 2": (0.322, 0.769, 0.725),

            "obsidian": (0.29, 0.16, 0.35),
            "visual studio code": (0.4, 0.4, 0.4),
            # "messages": (0.7, 0.85, 0.6),
            "messages": (1, 0.376, 0.376),
            # "safari": (0.7, 0.88, 1),
            "safari": (0.988, 0.686, 0.486),
            "reminders": (0.678, 0.961, 0.855),
            "books": (0.929, 0.761, 0.922),
            "notes": (0.969, 0.898, 0.486)
        }


    def get_color(self, identifier):
        # check if app already has a color assigned
        if identifier in self.app_colors:
            color = self.app_colors[identifier]

        # check if the app has a preset color
        elif identifier in self.preset_colors:
            self.app_colors[identifier] = self.preset_colors[identifier]
            color = self.preset_colors[identifier]

        # assign a new color from the color cycle
        else:
            color = self.color_map[self.color_index]
            self.app_colors[identifier] = color
            # cycle through colors
            self.color_index = (self.color_index + 1) % len(self.color_map)

        return color




if __name__ == "__main__":
    timer = TaskTimerSh()
    # timer.generate_visualizations(filepath="./data/activity_logs/20241205_activity_log.txt")