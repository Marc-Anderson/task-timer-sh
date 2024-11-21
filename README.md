# task-timer-sh

a zsh only utility for recording a timeline of the active application and how long each app has been active for the day

## considerations

- currently only works in macos
- logs application names only, does not track window titles
- no external resources, all files are saved locally in the `logs` folder
- terminal window must remain open to continue logging


## what does it do

1. creates a `logs` folder in the current directory if it doesnt exist
2. loads the `tracker_log.txt` into an array if it exists
3. makes a note of which app is in the foreground and the current time
4. checks every 1s if
    - the foreground application has changed
    - the computer has been idle for more than the idle time(45s)(the foreground app changes to `Idle`)
5. when the foreground app changes
6. records an entry into `./logs/YYYYMMDD_activity_log.txt` with the start_datetime, end_datetime, application_title, and duration
7. adds the duration to the appropriate application in `./logs/YYYYMMDD_tracker_log.txt`
    - it actually keeps an array in memory of all of the applications and their durations, and rewrites all of them when the foreground app changes
    - this is a holdover from when i had been just constantly incrementing it, may change this in the future
8. when the idle time is reached(45s) the idle time is subtracted from the previously active app and it is added to `Idle`
9. exit the application with `control+c`
10. script writes to both files one last time on exit


## why does this exist

in the age of excessive telemetry and advertising, i dont trust anyone but i wanted to be able to look back on my day to see what i was doing at a specific time. i track my hours for work and sometimes i forget to log switching to a new task. i wanted a very simple utility written in an uncomplicated way that i could refer to when i slipped up.


## future development

- i hope to make this compatible with windows at some point, so i can use it when im on a pc
- i also hope to add some post-processing tools so i can extract a schedule from the activity_log 


## how is it used

i usually do this in a seperate tab in the terminal app, not vscode since the session needs to remain open for it to continue logging

1. clone the repo
```sh
git clone git@github.com:Marc-Anderson/task-timer-sh.git
```

2. cd into the folder
```sh
cd task-timer-sh
```

3. make the `task-timer.sh` executable
```sh
chmod +x ./task-timer.sh
```

4. start `task-timer.sh`
```sh
./task-timer.sh
```

5. keep the terminal window open while you do work and the results will be saved in each file