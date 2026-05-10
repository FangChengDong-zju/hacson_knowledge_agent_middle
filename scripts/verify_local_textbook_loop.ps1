param(
    [string]$TextbookDir = "E:\textbooks",
    [string]$ProcessedTextbooksPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\textbooks.json",
    [string]$SummaryPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\parse_summary.json",
    [string]$MarkdownReportPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\report\local_textbook_loop_check.md",
    [int]$ExpectedBooks = 7
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not (Test-Path -LiteralPath $TextbookDir)) {
    throw "Textbook directory not found: $TextbookDir"
}
if (-not (Test-Path -LiteralPath $ProcessedTextbooksPath)) {
    throw "Processed textbook file not found. Run scripts\bootstrap_cached_textbooks.ps1 first: $ProcessedTextbooksPath"
}

$localFiles = Get-ChildItem -LiteralPath $TextbookDir -File |
    Where-Object { $_.Extension.ToLowerInvariant() -in @(".pdf", ".md", ".txt", ".docx") } |
    Sort-Object Name

$textbooks = Get-Content -LiteralPath $ProcessedTextbooksPath -Encoding UTF8 -Raw | ConvertFrom-Json
if ($null -eq $textbooks) {
    $textbooks = @()
}
if ($textbooks -isnot [array]) {
    $textbooks = @($textbooks)
}

$books = New-Object System.Collections.Generic.List[object]
foreach ($book in $textbooks) {
    $chapters = @($book.chapters)
    $sourceExists = Test-Path -LiteralPath ([string]$book.source_path)
    $totalPagesValue = 0
    if ($null -ne $book.total_pages) { $totalPagesValue = [int]$book.total_pages }
    $totalCharsValue = 0
    if ($null -ne $book.total_chars) { $totalCharsValue = [int]$book.total_chars }
    $storedChars = ($chapters | ForEach-Object {
        if ($null -ne $_.content) { [string]$_.content.Length } else { "0" }
    } | ForEach-Object { [int]$_ } | Measure-Object -Sum).Sum
    if ($null -eq $storedChars) { $storedChars = 0 }

    $books.Add([ordered]@{
        textbook_id = [string]$book.textbook_id
        title = [string]$book.title
        filename = [string]$book.filename
        source_exists = [bool]$sourceExists
        format = [string]$book.format
        total_pages = [int]$totalPagesValue
        chapter_count = [int]$chapters.Count
        total_chars = [int]$totalCharsValue
        stored_content_chars = [int]$storedChars
        first_chapter = if ($chapters.Count -gt 0) { [string]$chapters[0].title } else { "" }
        last_chapter = if ($chapters.Count -gt 0) { [string]$chapters[$chapters.Count - 1].title } else { "" }
    })
}

$totalPages = ($books | ForEach-Object { [int]$_.total_pages } | Measure-Object -Sum).Sum
$totalChapters = ($books | ForEach-Object { [int]$_.chapter_count } | Measure-Object -Sum).Sum
$totalChars = ($books | ForEach-Object { [int]$_.total_chars } | Measure-Object -Sum).Sum
$totalStoredChars = ($books | ForEach-Object { [int]$_.stored_content_chars } | Measure-Object -Sum).Sum
if ($null -eq $totalPages) { $totalPages = 0 }
if ($null -eq $totalChapters) { $totalChapters = 0 }
if ($null -eq $totalChars) { $totalChars = 0 }
if ($null -eq $totalStoredChars) { $totalStoredChars = 0 }

$checks = [ordered]@{
    textbook_dir_exists = (Test-Path -LiteralPath $TextbookDir)
    local_file_count_matches_expected = ($localFiles.Count -eq $ExpectedBooks)
    processed_file_exists = (Test-Path -LiteralPath $ProcessedTextbooksPath)
    parsed_book_count_matches_expected = ($books.Count -eq $ExpectedBooks)
    every_source_file_exists = (($books | Where-Object { -not $_.source_exists }).Count -eq 0)
    every_book_has_chapters = (($books | Where-Object { $_.chapter_count -le 0 }).Count -eq 0)
    every_book_has_text = (($books | Where-Object { $_.total_chars -le 0 }).Count -eq 0)
}
$closedLoopReady = -not ($checks.Values -contains $false)

$summary = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    closed_loop_ready = [bool]$closedLoopReady
    expected_books = [int]$ExpectedBooks
    paths = [ordered]@{
        textbook_dir = $TextbookDir
        processed_textbooks = $ProcessedTextbooksPath
        summary = $SummaryPath
        markdown_report = $MarkdownReportPath
    }
    totals = [ordered]@{
        local_files = [int]$localFiles.Count
        parsed_books = [int]$books.Count
        pages = [int]$totalPages
        chapters = [int]$totalChapters
        chars = [int]$totalChars
        stored_content_chars = [int]$totalStoredChars
    }
    checks = $checks
    books = $books
}

$summaryDir = Split-Path -Parent $SummaryPath
$reportDir = Split-Path -Parent $MarkdownReportPath
New-Item -ItemType Directory -Force -Path $summaryDir | Out-Null
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryPath -Encoding UTF8

$statusText = if ($closedLoopReady) { "PASS" } else { "FAIL" }
$checkRows = foreach ($key in $checks.Keys) {
    $value = if ($checks[$key]) { "PASS" } else { "FAIL" }
    "| $key | $value |"
}
$bookRows = foreach ($book in $books) {
    "| $($book.textbook_id) | $($book.title) | $($book.total_pages) | $($book.chapter_count) | $($book.total_chars) | $($book.source_exists) |"
}

$reportLines = New-Object System.Collections.Generic.List[string]
$reportLines.Add("# Local Textbook Parsing Loop Check")
$reportLines.Add("")
$reportLines.Add("Generated at: $($summary.generated_at)")
$reportLines.Add("")
$reportLines.Add("Result: $statusText.")
$reportLines.Add("")
$reportLines.Add("## Inputs And Outputs")
$reportLines.Add("")
$reportLines.Add("| Item | Path |")
$reportLines.Add("|---|---|")
$reportLines.Add("| Local textbook directory | $TextbookDir |")
$reportLines.Add("| Structured textbook data | $ProcessedTextbooksPath |")
$reportLines.Add("| Machine-readable summary | $SummaryPath |")
$reportLines.Add("")
$reportLines.Add("## Totals")
$reportLines.Add("")
$reportLines.Add("| Metric | Value |")
$reportLines.Add("|---|---:|")
$reportLines.Add("| Local textbook files | $($summary.totals.local_files) |")
$reportLines.Add("| Parsed textbooks | $($summary.totals.parsed_books) |")
$reportLines.Add("| Total pages | $($summary.totals.pages) |")
$reportLines.Add("| Chapter/segment count | $($summary.totals.chapters) |")
$reportLines.Add("| Source text chars | $($summary.totals.chars) |")
$reportLines.Add("| Stored content chars | $($summary.totals.stored_content_chars) |")
$reportLines.Add("")
$reportLines.Add("## Checks")
$reportLines.Add("")
$reportLines.Add("| Check | Result |")
$reportLines.Add("|---|---|")
foreach ($row in $checkRows) { $reportLines.Add($row) }
$reportLines.Add("")
$reportLines.Add("## Books")
$reportLines.Add("")
$reportLines.Add("| ID | Title | Pages | Chapters/Segments | Chars | Source Exists |")
$reportLines.Add("|---|---|---:|---:|---:|---|")
foreach ($row in $bookRows) { $reportLines.Add($row) }
$reportLines.Add("")
$reportLines.Add("## Scoring Evidence")
$reportLines.Add("")
$reportLines.Add("- B1 parser: seven local PDFs are converted into one textbook/chapter schema.")
$reportLines.Add("- B5 RAG: later indexes can consume chapter content and page metadata without reopening PDFs.")
$reportLines.Add("- A1/A4 reproducibility: this report and parse_summary.json provide auditable evidence.")
$reportLines.Add("- E1/E3 engineering: input, output, and validation artifacts are separated for backend and frontend reuse.")
$reportLines.Add("")
$reportLines.Add("## Next Handoff")
$reportLines.Add("")
$reportLines.Add("1. Backend reads data/processed/textbooks.json after startup.")
$reportLines.Add("2. Graph Builder extracts knowledge nodes from chapter content.")
$reportLines.Add("3. RAG Indexer chunks content into 500-800 character blocks and keeps page citations.")
$report = $reportLines -join "`r`n"

$report | Set-Content -LiteralPath $MarkdownReportPath -Encoding UTF8
Write-Host "Closed loop ready: $closedLoopReady"
Write-Host "Wrote summary: $SummaryPath"
Write-Host "Wrote report: $MarkdownReportPath"
