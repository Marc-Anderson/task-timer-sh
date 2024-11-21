#!/bin/sh

# # check for required arguments
# if [ $# -ne 1 ]; then
#     echo "NEEDED: File to write statistics to"
#     exit 1
# fi

# not tested
# `nohup ./your_script.sh > output.log 2>&1 &`
# `nohup` allows the script to keep running even after the terminal is closed
# `> output.log` redirects the output to a log file (you can name it whatever you want)
# `2>&1` redirects any errors to the same log file
# `&` runs the command in the background
# not necessary 
# `caffeinate -s ./your_script.sh`
# caffeinate is a built-in macOS utility that prevents the system from sleeping
# `-s` tells caffeinate to prevent the system from sleeping as long as the script is running


# # working with datetimes - save the datetime as epoch time
# lastLogEpochTime=$(date +%s)
# echo "epoch time: $lastLogEpochTime"
# # convert the epoch time to a human readable format
# echo "$(date -r "$lastLogEpochTime" "+%Y-%m-%d %H:%M:%S")"
# # calculate the difference in seconds
# secondsSinceLastLog="$(echo "$(date +%s) - $lastLogEpochTime" | bc)"
# echo "seconds since last log: $secondsSinceLastLog"
# lastLogEpochTime=$(date +%s)

# statisticsFile="$1"
statisticsFile="./logs/$(date +%Y%m%d)_tracker_log.txt"
activityLogFile="./logs/$(date +%Y%m%d)_activity_log.txt"

# create the logs directory if it doesn't exist
if [ ! -d "./logs" ]; then
    mkdir "./logs"
fi

# time to consider as idle
maxIdleTime=45.0

# frequency to check for updates
updateEvery=1

# frequency to write to tracker file
writeEvery=10


# region load and write statistics

# load the previous statistics from the file
loadStatistics() {

    index=0
    # read each line in the file using : as a separator
    echo "loading app data:"

    while IFS=':' read -r appName activeTime; do
        # # debug: print the values during processing
        # echo "$appName -- $activeTime"
        # get references to each value and assign them to the arrays
        usedAppNames[index]="$appName"
        usedAppTimes[index]="$activeTime"
        # 
        index=$((index + 1))
    done < "$statisticsFile"

    # # debug: print the values after processing
    # echo "<START-debugging>"
    # loop_index=0
    # for appName in "${usedAppNames[@]}"; do
    #     echo "Key: ${appName}, Value: ${usedAppTimes[loop_index]}"
    #     loop_index=$((loop_index + 1))
    # done
    # echo "<END-debugging>"

}



# write statistics to file
writeStatistics() {

    loop_index=0
    for appName in "${usedAppNames[@]}"; do
        echo "$appName:${usedAppTimes[loop_index]}"
        loop_index=$((loop_index + 1))
    done | sort -t: -k2nr > "$statisticsFile"
    # -t:: field separator(:)
    # -k2: set sorting key as second field. fields numbered starting from 1
    # n: numeric sort
    # r: reverse sort
}

# endregion load and write statistics


# region private variables

# when the app started
startTime=$(date +%s)

# macos uses bash 3.2 which doesnt support associative arrays
declare -a usedAppNames
declare -a usedAppTimes

# the previously active app and its start time
previousApp=""
previousAppStartEpochDatetime="$startTime"

# running iterations
i=0

# initialize the idle toggle to not idle
idleToggle=0

# endregion private variables


# region signal handling

# cleanup before exiting the application
cleanup() {
    echo "saving data before exit"
    # log the end time of the previous app
    # local formattedPreviousAppStartEpochDatetime=$(date -r "$previousAppStartEpochDatetime" "+%Y-%m-%d %H:%M:%S")
    # local currentDatetimeTimestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # calculate the time to add to the previous app
    timeToAdd=$(( $(date +%s) - previousAppStartEpochDatetime ))

    # add the time to the app in the list
    addTimeToApp "$previousApp" "$timeToAdd"

    # log the activity to the activity log
    logActivityEpochTime "$previousApp" "$previousAppStartEpochDatetime" "$(date +%s)"

    # clear statistics file and write the updated statistics
    echo "" > "$statisticsFile"
    writeStatistics 

    # additional commands to execute before exit
}

# set trap to call the cleanup on EXIT
trap cleanup EXIT


# endregion signal handling



# 
echo "begining active app time tracking..."

# load existing statistics if any
[ -f "$statisticsFile" ] && loadStatistics


# region helper functions


# get the index of the app from the list
getIndexOfApp() {
    local name="$1"
    # look through the indicies of names
    for i in "${!usedAppNames[@]}"; do
        # check each index for the name
        if [[ "${usedAppNames[i]}" == "$name" ]]; then
            # return index of the name, found
            echo $i
            return 0
        fi
    done
    # return empty string, name not found
    echo ""
    return 1
}


addTimeToApp() {

    local activeApp="$1"
    local timeToAdd="$2"

    # get the index of the app from the list
    local indexOfApp=$(getIndexOfApp "$activeApp")

    # check if the app is already in the list
    if [[ -z "$indexOfApp" || "$indexOfApp" == "" ]]; then
        usedAppNames+=("$activeApp")
        usedAppTimes+=(0)
        indexOfApp=$((${#usedAppNames[@]} - 1))
    fi

    # current time
    local appsCurrentTime=${usedAppTimes[$indexOfApp]}

    # add the time to the app
    local updatedTime=$(echo "$appsCurrentTime + $timeToAdd" | bc)

    # # debug
    # echo "updating app time: $activeApp - new: $updatedTime, old: $appsCurrentTime"

    # ensure the time doesn't go below zero
    if (( $(echo "$updatedTime < 0" | bc) )); then
        # echo "warning: time for $activeApp cannot go below zero. setting to zero."
        usedAppTimes[$indexOfApp]=0
    else
        usedAppTimes[$indexOfApp]=$updatedTime
    fi
}




# record to the activity log
logActivityEpochTime() {
    local appName="$1"
    local startEpochTime="$2"
    local stopEpochTime="$3"

    # ensure all values are set
    if [[ -z "$appName" || -z "$startEpochTime" || -z "$stopEpochTime" ]]; then
        return
    fi

    # calculate the duration in seconds between the dates
    local duration=$(( stopEpochTime - startEpochTime ))

    # if the duration is less than or equal to 0, don't log
    if (( duration <= 0 )); then
        return
    fi

    # calculate hours, minutes, and seconds
    local hours=$(( duration / 3600 ))
    local minutes=$(( (duration % 3600) / 60 ))
    local seconds=$(( duration % 60 ))

    # format the duration with at least 2 digits for hours
    local formattedDuration=$(printf "%02d:%02d:%02d" $hours $minutes $seconds)

    # Format the start and stop times to human readable format
    local formattedStartTime="$(date -r "$startEpochTime" "+%Y-%m-%d %H:%M:%S")"
    local formattedStopTime="$(date -r "$stopEpochTime" "+%Y-%m-%d %H:%M:%S")"

    echo "$formattedStartTime - $formattedStopTime($formattedDuration): $appName" >> "$activityLogFile"
}


# endregion helper functions 



# region main loop

# main loop to track application usage
while true; do
    # # keep track of loop or script time to exit after a certain time if needed
    # elapsedTimeInSeconds="$(( $(date +%s) - startTime ))"

    # set the current date time for the bases of all calculations in this iteration
    currentEpochDatetime="$(date +%s)"
    
    # get the application name
    activeApp=$(lsappinfo info `lsappinfo front | sed 's/-/-0x/'` | grep 'bundle path' | sed 's/"//g' | awk -F '=' '{print $NF}' | sed 's/\.app$//' | awk -F'/' '{print $NF}')

    # get the idle time from io registry(input device idle time) as an integer
    idleTimeInSeconds=$(ioreg -c IOHIDSystem | grep Idle | awk '{print int($NF/1000000000)}')

    # check if idle time is less than max idle time
    if (( $(echo "$idleTimeInSeconds < $maxIdleTime" | bc -l) )); then

        # ensure the idle toggle is reset if the app is active
        idleToggle=0

    else

        # set the active app to idle
        activeApp="Idle"

        # if this is the first idle signal, we need to adjust the current date time to account for the idle delay
        if [[ $idleToggle -eq 0 ]]; then

            # set the idle toggle to 1
            idleToggle=1

            # subtract the idle time from the current date time
            currentEpochDatetime=$((currentEpochDatetime - idleTimeInSeconds))

        fi

    fi


    # if the user changes apps
    if [[ "$activeApp" != "$previousApp" ]]; then

        # ensure there is a previous app before trying to record it, `-n` checks the length of the value to see if its empty, skips this section on the first iteration
        if [[ -n "$previousApp" ]]; then

            # calculate the time to add to the previous app
            timeToAdd=$((currentEpochDatetime - previousAppStartEpochDatetime))

            # add the time to the app in the list
            addTimeToApp "$previousApp" "$timeToAdd"

            # log the activity to the activity log
            logActivityEpochTime "$previousApp" "$previousAppStartEpochDatetime" "$currentEpochDatetime"

            # clear statistics file and write the updated statistics
            echo "" > "$statisticsFile"
            writeStatistics 

        fi

        # update previous app and start time
        previousApp="$activeApp"
        previousAppStartEpochDatetime="$currentEpochDatetime"
    fi


    # sleep for update interval
    sleep $updateEvery


    # if (( i % 10 == 0 )); then
    #     echo "aapp: $activeApp; papp: $previousApp; addedTime: $timeToAdd; idle: $idleTimeInSeconds"
    # fi

    # increment the iteration
    i=$(( i + 1 ))

    # # write to file at specified intervals
    # if (( i % writeEvery == 0 )); then
    #     # clear the file before writing
    #     echo "" > "$statisticsFile"
    #     writeStatistics 
    # fi


done

# endregion main loop



# # # get information about the previously active window
# sleep 3
# lsappinfo info `lsappinfo front | sed 's/-/-0x/'` 
# # "Terminal" ASN:0x0-4c04c: (in front) 
# #     bundleID="com.apple.Terminal"
# #     bundle path="/System/Applications/Utilities/Terminal.app"
# #     executable path="/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal"
# #     pid = 1999 type="Foreground" flavor=3 Version="453" fileType="APPL" creator="????" Arch=ARM64 
# #     parentASN="Spotlight" ASN:0x1-0x291: 
# #     launch time =  2024/08/11 08:39:35 ( 31 minutes, 20.7215 seconds ago )
# #     checkin time = 2024/08/11 08:39:35 ( 31 minutes, 20.6641 seconds ago )
# #     launch to checkin time: 0.0573549 seconds

# pid=$(lsappinfo info `lsappinfo front | sed 's/-/-0x/'` | grep -o 'pid = [0-9]*' | awk '{print $3}')


# ways to organize weekly data
# StartDateTime:NameOfApp:StopDateTime:DurationInSeconds
# DateTime:NameOfApp: