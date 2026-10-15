param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference='Stop'
if (-not (Test-Path -LiteralPath $Source)) { throw 'Source does not exist' }
Move-Item -LiteralPath $Source -Destination $Destination -Force -ErrorAction Stop
