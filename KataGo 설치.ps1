# KataGo 자동 설치기
#
# 하는 일
#   1. GitHub 최신 릴리스에서 Windows 용 KataGo 를 받아 압축을 푼다
#   2. 신경망 내려받는 페이지를 브라우저로 열어준다
#   3. 받아진 .bin.gz 를 자동으로 찾아 제자리에 옮긴다
#   4. 잘 되는지 확인한다
#
# 기본 설치 위치는 이 폴더의 부모 아래 katago\ 다.
# 즉 "D:\...\6. 바둑\KataGo 설치.bat" 을 실행하면 "D:\...\katago\" 에 깔린다.
# 다른 곳에 깔려면 경로를 인자로 준다:
#     KataGo 설치.bat "D:\내가\원하는\곳"

param(
    [string]$경로 = "",
    [string]$Mode = "opencl"
)

$ErrorActionPreference = "Stop"

if ($경로) {
    $집 = $경로
} else {
    # 이 스크립트가 있는 폴더의 부모 아래 katago
    $집 = Join-Path (Split-Path -Parent $PSScriptRoot) "katago"
}

function 알림($글) { Write-Host $글 -ForegroundColor Cyan }
function 나쁨($글) { Write-Host $글 -ForegroundColor Red }
function 좋음($글) { Write-Host $글 -ForegroundColor Green }

Write-Host ""
알림 "============================================"
알림 "  KataGo 설치"
알림 "============================================"
Write-Host ""
Write-Host "설치 위치: $집"
Write-Host "  (다른 곳에 깔려면: KataGo 설치.bat \"D:\원하는\경로\")"
Write-Host ""

New-Item -ItemType Directory -Force -Path $집 | Out-Null

# ----------------------------------------------------------------------
# 1. 실행 파일
# ----------------------------------------------------------------------
$실행파일 = Join-Path $집 "katago.exe"
if (Test-Path $실행파일) {
    좋음 "KataGo 실행 파일이 이미 있습니다. 건너뜁니다."
} else {
    알림 "[1/4] KataGo 최신 판을 찾는 중..."
    try {
        $릴리스 = Invoke-RestMethod -Uri "https://api.github.com/repos/lightvector/KataGo/releases/latest" `
                                    -Headers @{ "User-Agent" = "go-baduk-installer" }
    } catch {
        나쁨 "GitHub 에 연결하지 못했습니다: $_"
        나쁨 "인터넷 연결을 확인하고 다시 실행하세요."
        Read-Host "Enter 를 누르면 닫힙니다"
        exit 1
    }

    $찾을것 = if ($Mode -eq "cpu") { "*eigen*windows*.zip" } else { "*opencl*windows*.zip" }
    $자산 = $릴리스.assets | Where-Object { $_.name -like $찾을것 } | Select-Object -First 1
    if (-not $자산) {
        나쁨 "맞는 파일을 못 찾았습니다. 직접 받아주세요:"
        나쁨 "  https://github.com/lightvector/KataGo/releases/latest"
        Read-Host "Enter 를 누르면 닫힙니다"
        exit 1
    }

    Write-Host "  버전: $($릴리스.tag_name)"
    Write-Host "  파일: $($자산.name)  ($([math]::Round($자산.size/1MB,1)) MB)"
    알림 "  내려받는 중... (1~2분)"

    $압축 = Join-Path $env:TEMP $자산.name
    $예전진행 = $ProgressPreference
    $ProgressPreference = "SilentlyContinue"      # 이게 있어야 훨씬 빠르다
    Invoke-WebRequest -Uri $자산.browser_download_url -OutFile $압축
    $ProgressPreference = $예전진행

    알림 "  압축 푸는 중..."
    $임시 = Join-Path $env:TEMP "katago_tmp"
    if (Test-Path $임시) { Remove-Item $임시 -Recurse -Force }
    Expand-Archive -Path $압축 -DestinationPath $임시 -Force

    # zip 안에 폴더가 한 겹 더 있을 수 있으므로 실제 위치를 찾아 옮긴다
    $찾은 = Get-ChildItem -Path $임시 -Filter "katago.exe" -Recurse | Select-Object -First 1
    if (-not $찾은) { 나쁨 "압축 안에서 katago.exe 를 못 찾았습니다."; Read-Host; exit 1 }
    Get-ChildItem -Path $찾은.DirectoryName | Move-Item -Destination $집 -Force

    Remove-Item $임시 -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $압축 -Force -ErrorAction SilentlyContinue
    좋음 "  실행 파일 설치 완료"
}

# ----------------------------------------------------------------------
# 2. 신경망
# ----------------------------------------------------------------------
$신경망 = Get-ChildItem -Path $집 -Filter "*.bin.gz" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($신경망) {
    좋음 "신경망이 이미 있습니다: $($신경망.Name)"
} else {
    Write-Host ""
    알림 "[2/4] 신경망 파일이 필요합니다."
    Write-Host ""
    Write-Host "  브라우저를 엽니다. 목록 맨 위쪽 최신 것에서" -ForegroundColor Yellow
    Write-Host "  .bin.gz 파일을 하나 받으세요." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  b18 계열이면 충분히 강합니다 (100~200MB)."
    Write-Host "  컴퓨터가 느리면 b6 나 b10 처럼 작은 것을 고르세요."
    Write-Host ""
    Start-Sleep -Seconds 2
    Start-Process "https://katagotraining.org/networks/"

    $받는곳 = Join-Path $env:USERPROFILE "Downloads"
    알림 "  다운로드 폴더를 지켜보는 중... (최대 15분, Ctrl+C 로 중단)"
    $시작 = Get-Date
    $받은것 = $null
    while (-not $받은것 -and ((Get-Date) - $시작).TotalMinutes -lt 15) {
        Start-Sleep -Seconds 3
        $받은것 = Get-ChildItem -Path $받는곳 -Filter "*.bin.gz" -ErrorAction SilentlyContinue |
                  Where-Object { $_.LastWriteTime -gt $시작 } |
                  Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }

    if (-not $받은것) {
        나쁨 "  신경망을 못 찾았습니다."
        나쁨 "  받으신 .bin.gz 파일을 직접 이 폴더에 넣어주세요: $집"
        Read-Host "Enter 를 누르면 닫힙니다"
        exit 1
    }

    # 아직 받는 중일 수 있으니 크기가 안 변할 때까지 기다린다
    $이전크기 = -1
    while ($이전크기 -ne $받은것.Length) {
        $이전크기 = $받은것.Length
        Start-Sleep -Seconds 2
        $받은것.Refresh()
    }
    Move-Item -Path $받은것.FullName -Destination $집 -Force
    좋음 "  신경망 설치 완료: $($받은것.Name)"
}

# ----------------------------------------------------------------------
# 3. 확인
# ----------------------------------------------------------------------
Write-Host ""
알림 "[3/4] 잘 도는지 확인합니다..."
try {
    $판 = & $실행파일 version 2>&1 | Select-Object -First 1
    좋음 "  $판"
} catch {
    나쁨 "  실행에 실패했습니다: $_"
    if ($Mode -ne "cpu") {
        나쁨 "  그래픽카드 문제일 수 있습니다. CPU 판으로 다시 해보세요:"
        나쁨 "     KataGo 설치.bat \"\" cpu"
    }
    Read-Host "Enter 를 누르면 닫힙니다"
    exit 1
}

Write-Host ""
알림 "[4/4] 끝났습니다."
Write-Host ""
# 바둑 프로그램이 찾을 수 있도록 경로를 적어 둔다.
$쪽지 = Join-Path $PSScriptRoot "katago경로.txt"
Set-Content -Path $쪽지 -Value $집 -Encoding UTF8
Write-Host "  경로를 katago경로.txt 에 적어 두었습니다."
Write-Host "  이제 바둑 프로그램이 KataGo 를 자동으로 찾습니다."
Write-Host ""
Write-Host "  확인:   python baduk.py engines"
Write-Host "  대국:   python baduk.py"
Write-Host ""
Write-Host "  * 처음 두는 수는 오래 걸립니다 (그래픽카드 맞춤 설정, 3~10분)."
Write-Host "    한 번만 하면 다음부터는 빠릅니다."
Write-Host ""
Write-Host "  * 너무 세면 약하게 두세요:"
Write-Host "      python baduk.py --탐색수 20"
Write-Host "      python baduk.py --접바둑 4"
Write-Host ""
Read-Host "Enter 를 누르면 닫힙니다"
