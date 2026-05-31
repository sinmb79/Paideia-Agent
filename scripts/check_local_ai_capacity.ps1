$ErrorActionPreference = "Stop"

$computer = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor
$gpu = Get-CimInstance Win32_VideoController
$drives = Get-PSDrive -PSProvider FileSystem

Write-Host "[LOCAL AI CAPACITY]"
Write-Host ("RAM_GB=" + [math]::Round($computer.TotalPhysicalMemory / 1GB, 2))
foreach ($item in $cpu) {
    Write-Host ("CPU=" + $item.Name)
    Write-Host ("CPU_CORES=" + $item.NumberOfCores)
    Write-Host ("CPU_THREADS=" + $item.NumberOfLogicalProcessors)
}
foreach ($item in $gpu) {
    Write-Host ("GPU=" + $item.Name)
    if ($item.AdapterRAM) {
        Write-Host ("GPU_ADAPTER_RAM_GB=" + [math]::Round($item.AdapterRAM / 1GB, 2))
    }
    Write-Host ("GPU_DRIVER=" + $item.DriverVersion)
}
foreach ($drive in $drives) {
    Write-Host ("DRIVE_" + $drive.Name + "_FREE_GB=" + [math]::Round($drive.Free / 1GB, 2))
}

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    Write-Host "[NVIDIA]"
    nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader
}
else {
    Write-Host "[NVIDIA] nvidia-smi not found"
}
