# Compila el informe (pdflatex + biber + pdflatex x2) en la carpeta build/
# y copia el resultado a informe_final.pdf.
# Uso: desde Documentation, ejecutar  .\build.ps1
# Requiere MiKTeX (o TeX Live) con pdflatex y biber.
$bin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
if (Test-Path "$bin\pdflatex.exe") { $env:PATH = "$bin;$env:PATH" }
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force build | Out-Null
$texArgs = @("-interaction=nonstopmode", "-halt-on-error", "-output-directory=build", "main.tex")

# MiKTeX escribe avisos en stderr (por ejemplo, de actualizaciones); se evalúa
# solo el código de salida de cada paso.
function Invoke-Step([string]$name, [string[]]$stepArgs) {
    & $name @stepArgs 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Output "Falló $name (código $LASTEXITCODE). Ver build\main.log o build\main.blg."
        exit $LASTEXITCODE
    }
}

Invoke-Step "pdflatex" $texArgs
Invoke-Step "biber" @("--input-directory", "build", "--output-directory", "build", "main")
Invoke-Step "pdflatex" $texArgs
Invoke-Step "pdflatex" $texArgs
Copy-Item build\main.pdf informe_final.pdf -Force
Write-Output "PDF generado: informe_final.pdf"
