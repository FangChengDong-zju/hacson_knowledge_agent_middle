$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$HealthDemoPython = "E:\codex test\Preparation for Hacson\health_agent_demo\.venv\Scripts\python.exe"
$LocalPython = "C:\Users\29434\AppData\Local\Programs\Python\Python311\python.exe"
$Port = 8502

if (Test-Path -LiteralPath $HealthDemoPython) {
    $Python = $HealthDemoPython
} elseif (Test-Path -LiteralPath $LocalPython) {
    $Python = $LocalPython
} else {
    throw "No Python runtime found. Checked health_agent_demo venv and local Python 3.11."
}

& $LocalPython "$ProjectRoot\scripts\build_integration_demo.py"
& $LocalPython "$ProjectRoot\scripts\build_final_report.py"

Write-Host "Starting Hacson Streamlit demo..."
Write-Host "URL: http://127.0.0.1:$Port"
& $Python -m streamlit run "$ProjectRoot\streamlit_app.py" --server.port $Port --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
