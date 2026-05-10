param(
    [string]$ChunksPath = "E:\codex test\Preparation for Hacson\health_agent_demo\data\textbook_chunks.jsonl",
    [string]$StatsPath = "E:\codex test\Preparation for Hacson\health_agent_demo\reports\textbook_index_stats.json",
    [string]$OutputPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\textbooks.json",
    [int]$PagesPerChapter = 25
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ChunksPath)) {
    throw "Chunks file not found: $ChunksPath"
}
if (-not (Test-Path -LiteralPath $StatsPath)) {
    throw "Stats file not found: $StatsPath"
}

$stats = Get-Content -LiteralPath $StatsPath -Encoding UTF8 -Raw | ConvertFrom-Json
$bookStats = @{}
foreach ($book in $stats.books) {
    $bookStats[$book.book_id] = $book
}

$grouped = @{}
Get-Content -LiteralPath $ChunksPath -Encoding UTF8 | ForEach-Object {
    if (-not $_.Trim()) { return }
    $chunk = $_ | ConvertFrom-Json
    $bookId = [string]$chunk.book_id
    if (-not $grouped.ContainsKey($bookId)) {
        $grouped[$bookId] = New-Object System.Collections.Generic.List[object]
    }
    $grouped[$bookId].Add($chunk)
}

$textbooks = New-Object System.Collections.Generic.List[object]
$order = 1
foreach ($bookId in ($grouped.Keys | Sort-Object)) {
    $chunks = $grouped[$bookId]
    $first = $chunks[0]
    $stat = $bookStats[$bookId]
    $textbookId = "book_{0:D3}" -f $order

    $buckets = @{}
    foreach ($chunk in $chunks) {
        $page = [int]$chunk.page
        if ($page -lt 1) { $page = 1 }
        $bucket = [int][math]::Floor(($page - 1) / $PagesPerChapter)
        if (-not $buckets.ContainsKey($bucket)) {
            $buckets[$bucket] = New-Object System.Collections.Generic.List[object]
        }
        $buckets[$bucket].Add($chunk)
    }

    $chapters = New-Object System.Collections.Generic.List[object]
    $chapterIndex = 1
    foreach ($bucket in ($buckets.Keys | Sort-Object {[int]$_})) {
        $bucketChunks = $buckets[$bucket]
        $pages = @($bucketChunks | ForEach-Object { [int]$_.page })
        $pageStart = ($pages | Measure-Object -Minimum).Minimum
        $pageEnd = ($pages | Measure-Object -Maximum).Maximum
        $content = ($bucketChunks | ForEach-Object { [string]$_.text }) -join "`n"

        $chapters.Add([ordered]@{
            chapter_id = ("{0}_ch_{1:D3}" -f $textbookId, $chapterIndex)
            textbook_id = $textbookId
            title = ("Pages {0}-{1} knowledge segment" -f $pageStart, $pageEnd)
            page_start = $pageStart
            page_end = $pageEnd
            content = if ($content.Length -gt 18000) { $content.Substring(0, 18000) } else { $content }
            char_count = $content.Length
        })
        $chapterIndex += 1
    }

    $totalChars = ($chapters | ForEach-Object { [int]$_.char_count } | Measure-Object -Sum).Sum
    $textbooks.Add([ordered]@{
        textbook_id = $textbookId
        filename = [string]$first.source_file
        title = [string]$first.book_title
        format = "pdf"
        total_pages = if ($stat) { [int]$stat.pages } else { 0 }
        total_chars = [int]$totalChars
        status = "parsed"
        chapters = $chapters
        source_path = Join-Path "E:\textbooks" ([string]$first.source_file)
        error = $null
    })
    $order += 1
}

$outputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$textbooks | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

Write-Host "Wrote $($textbooks.Count) textbooks to $OutputPath"
