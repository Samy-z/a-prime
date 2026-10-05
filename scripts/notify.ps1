# Pop a Windows notification. Used by overnight.cmd when a run ends badly, so
# a failure at 5am is visible on screen instead of only in a log nobody has
# opened yet. The owner then pings the agent session to set things back up.
#
# Two layers, because Windows 11 Home offers no single dependable channel from
# a headless script: a WinRT toast first, and a tray balloon if the toast
# machinery refuses. Both are try/catch; worst case the failure is still in
# logs\overnight.log, which this supplements rather than replaces.
#
# What this cannot cover: a run that never started at all (laptop on battery at
# the trigger time, or nobody logged in). Nothing runs, so nothing can notify.
param(
    [string]$Title = "a-prime",
    [string]$Message = "run ended"
)

$toastOk = $false
try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
    $xml = @"
<toast scenario="reminder"><visual><binding template="ToastGeneric">
<text>$Title</text><text>$Message</text>
</binding></visual></toast>
"@
    $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
    $doc.LoadXml($xml)
    $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show(
        (New-Object Windows.UI.Notifications.ToastNotification($doc)))
    $toastOk = $true
} catch { }

if (-not $toastOk) {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $icon = New-Object System.Windows.Forms.NotifyIcon
        $icon.Icon = [System.Drawing.SystemIcons]::Warning
        $icon.Visible = $true
        $icon.ShowBalloonTip(15000, $Title, $Message, 'Warning')
        # The balloon dies with the process; give it time on screen.
        Start-Sleep -Seconds 12
        $icon.Dispose()
    } catch { }
}
