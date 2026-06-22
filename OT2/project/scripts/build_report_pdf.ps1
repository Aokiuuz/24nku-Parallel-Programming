$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir "..\..")
$source = Join-Path $root "project\docs\协程技术调研报告.md"
$projectAssets = Join-Path $root "project\assets"
$outputDir = Join-Path $root "final\pdf"
$outputAssets = Join-Path $outputDir "assets"
$buildLogDir = Join-Path $root "project\build"
$latexmkStdout = Join-Path $buildLogDir "report_latexmk.stdout.log"
$latexmkStderr = Join-Path $buildLogDir "report_latexmk.stderr.log"
$texPath = Join-Path $outputDir "协程技术调研报告.tex"
$pdfPath = Join-Path $outputDir "协程技术调研报告.pdf"
$fallbackPdfPath = Join-Path $outputDir "协程技术调研报告-更新版.pdf"
$buildJobName = "协程技术调研报告-latex-build"
$buildPdfPath = Join-Path $outputDir "$buildJobName.pdf"

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
New-Item -ItemType Directory -Path $outputAssets -Force | Out-Null
New-Item -ItemType Directory -Path $buildLogDir -Force | Out-Null

$markdown = Get-Content -LiteralPath $source -Raw
$imageMatches = [regex]::Matches($markdown, '!\[[^\]]*\]\(assets/([^)]+)\)')
$imageNames = $imageMatches | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique

foreach ($imageName in $imageNames) {
    $sourceImage = Join-Path $projectAssets $imageName
    if (-not (Test-Path -LiteralPath $sourceImage)) {
        throw "Missing report image: $sourceImage"
    }
    Copy-Item -LiteralPath $sourceImage -Destination (Join-Path $outputAssets $imageName) -Force
}

& pandoc `
    $source `
    --standalone `
    --from "markdown+yaml_metadata_block" `
    --to latex `
    --resource-path "$($root.Path)\project;$($root.Path)\project\docs" `
    --output $texPath

if ($LASTEXITCODE -ne 0) {
    throw "Pandoc failed with exit code $LASTEXITCODE"
}

Push-Location $outputDir
try {
    $latexmkArguments = @(
        "-g",
        "-xelatex",
        "-jobname=$buildJobName",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        (Split-Path -Leaf $texPath)
    )
    $latexmkProcess = Start-Process `
        -FilePath "latexmk" `
        -ArgumentList $latexmkArguments `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $latexmkStdout `
        -RedirectStandardError $latexmkStderr
    $latexmkExitCode = $latexmkProcess.ExitCode

    if ($latexmkExitCode -ne 0) {
        Get-Content -LiteralPath $latexmkStdout -Tail 40
        Get-Content -LiteralPath $latexmkStderr -Tail 40
        throw "latexmk failed with exit code $latexmkExitCode"
    }

    $finalPdfPath = $pdfPath
    try {
        Copy-Item -LiteralPath $buildPdfPath -Destination $pdfPath -Force -ErrorAction Stop
        if (Test-Path -LiteralPath $fallbackPdfPath) {
            Remove-Item -LiteralPath $fallbackPdfPath -Force
        }
    }
    catch {
        Copy-Item -LiteralPath $buildPdfPath -Destination $fallbackPdfPath -Force
        $finalPdfPath = $fallbackPdfPath
        Write-Warning "The canonical PDF is open or locked; wrote the updated PDF to $fallbackPdfPath"
    }

    foreach ($extension in ".aux", ".fdb_latexmk", ".fls", ".log", ".out", ".toc", ".xdv", ".pdf") {
        $generatedPath = Join-Path $outputDir "$buildJobName$extension"
        if (Test-Path -LiteralPath $generatedPath) {
            Remove-Item -LiteralPath $generatedPath -Force
        }
    }

    foreach ($extension in ".aux", ".fdb_latexmk", ".fls", ".log", ".out", ".toc", ".xdv") {
        $stalePath = Join-Path $outputDir "协程技术调研报告$extension"
        if (Test-Path -LiteralPath $stalePath) {
            Remove-Item -LiteralPath $stalePath -Force
        }
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $finalPdfPath)) {
    throw "Expected PDF was not generated: $finalPdfPath"
}

Write-Host "Generated LaTeX: $texPath"
Write-Host "Generated PDF:   $finalPdfPath"
