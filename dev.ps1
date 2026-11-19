# Sobe backend (porta 8000) e frontend (porta 5173), cada um numa janela.
# Uso: na pasta do projeto, rode  .\dev.ps1
$raiz = $PSScriptRoot

if (-not (Test-Path "$raiz\backend\.env")) {
    Copy-Item "$raiz\backend\.env.example" "$raiz\backend\.env"
    Write-Host "Criei backend\.env a partir do exemplo. Preencha as chaves quando chegar a Etapa 1B."
}

Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$raiz\backend'; uv run uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$raiz\frontend'; npm run dev"

Write-Host ""
Write-Host "Painel:   http://localhost:5173"
Write-Host "Backend:  http://localhost:8000/health"
Write-Host "API docs: http://localhost:8000/docs"
