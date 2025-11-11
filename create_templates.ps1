# Base templates directory
$baseDir = "templates"

# List of HTML files to create
$files = @(
    "cargo/tracking_list.html",
    "cargo/detail.html",
    "suppliers/list.html",
    "suppliers/detail.html",
    "warehouses/list.html",
    "warehouses/detail.html",
    "categories/list.html",
    "counties/list.html",
    "analytics/supplier_performance.html",
    "reports/list.html",
    "reports/detail.html",
    "alerts/list.html",
    "help/index.html",
    "help/documentation.html"
)

# Loop through each file path
foreach ($file in $files) {
    $path = Join-Path $baseDir $file
    $folder = Split-Path $path -Parent

    # Create directory if it doesn't exist
    if (!(Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
    }

    # Create empty HTML file if not exists
    if (!(Test-Path $path)) {
        New-Item -ItemType File -Path $path -Force | Out-Null
        # Optional: Add a basic HTML skeleton
        Add-Content -Path $path -Value "<!-- $file -->`n<!DOCTYPE html>`n<html>`n<head>`n    <title>$($file -replace '.html','')</title>`n</head>`n<body>`n    <h1>$($file -replace '.html','')</h1>`n</body>`n</html>"
    }
}

Write-Host "✅ All empty HTML files created successfully in the templates folder."
