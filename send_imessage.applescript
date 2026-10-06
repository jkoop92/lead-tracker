-- Sends a message via the Mac Messages app.
-- Usage: osascript send_imessage.applescript "+15551234567" "message text"
-- Tries iMessage first, falls back to SMS (requires Text Message Forwarding
-- set up with a paired iPhone) if the number isn't an iMessage user.
on run argv
    set thePhone to item 1 of argv
    set theMessage to item 2 of argv

    tell application "Messages"
        set targetBuddy to missing value
        try
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy thePhone of targetService
        on error
            try
                set targetService to 1st service whose service type = SMS
                set targetBuddy to buddy thePhone of targetService
            on error errMsg
                error "No iMessage or SMS service available for " & thePhone & ": " & errMsg
            end try
        end try
        send theMessage to targetBuddy
    end tell
end run
