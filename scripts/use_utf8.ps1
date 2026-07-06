# Use this before running bench/export/generation commands from Windows PowerShell.
# It prevents accented text from being downgraded to '?' when commands pass text via stdio.

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
chcp 65001 | Out-Null

Write-Host "PowerShell UTF-8 mode enabled for this session."
