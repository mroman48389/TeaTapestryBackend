# Session Cleanup

## 1. Local Setup via Windows Task Scheduler

> 1. Open Windows Task Scheduler:
>
>    Press Win + R, then type "taskschd.msc" and hit Enter.
>
> 2. Create a new task:
>
>    In the right panel, click "Create Task" (not Create Basic Task).
>    Name it something like "TeaTapestry Session Cleanup"
>
> 3. Set the trigger:
>
>    On the Triggers tab, go to New and choose "Daily". Set the time
>    you'd like the task to run, and select "Enabled". The task will now
>    run every day at this time.
>
> 4. Set the action:
>
>    On the Actions tab, go to New. Keep as "Start a program". Add the fully
>    qualified script file name for the path.
>
> 5. Set "Start in":
>
>    Add the path to the root folder of the project containing the script so
>    Python will not get confused by relative imports.
>
> 6. Other options:
>   
>    In General, select "Run whether user is logged on or not" and check 
>    "Run with highest privileges" so the job runs even if the machine is locked.
>    If you cannot create the task unless you choose the logged in option, you can 
>    still run the script via
>
>    `$env:PYTHONPATH="C:\Proj\TeaTapestryBackend"`
>    `python .\scripts\Maintenance\run_session_cleanup.py`
>
> You can view tasks you created if you click on Task Scheduler Library and 
> check in the panel to the right.
