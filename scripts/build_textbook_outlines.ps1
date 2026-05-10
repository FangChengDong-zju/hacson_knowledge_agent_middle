param(
    [string]$TextbooksPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\textbooks.json",
    [string]$TermsPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\backend\app\resources\core_terms.json",
    [string]$DemoOutputPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\outlines_demo.json",
    [string]$RuntimeOutputPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\outlines.json",
    [string]$SummaryPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\outline_summary.json",
    [string]$ReportPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\report\outline_build_check.md",
    [int]$MaxTermsPerChapter = 6,
    [int]$MaxRelatedPerTerm = 3
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function New-DirectoryForFile {
    param([string]$PathValue)
    $dir = Split-Path -Parent $PathValue
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

function Get-Snippet {
    param(
        [string]$Content,
        [string]$Term,
        [int]$Radius = 90
    )
    $index = $Content.IndexOf($Term)
    if ($index -lt 0) {
        $cleaned = [regex]::Replace($Content, "\s+", " ").Trim()
        if ($cleaned.Length -gt 220) { return $cleaned.Substring(0, 220) }
        return $cleaned
    }
    $start = [Math]::Max(0, $index - $Radius)
    $end = [Math]::Min($Content.Length, $index + $Term.Length + $Radius)
    $snippet = $Content.Substring($start, $end - $start)
    $snippet = [regex]::Replace($snippet, "\s+", " ").Trim()
    if ($snippet.Length -gt 220) { return $snippet.Substring(0, 220) }
    return $snippet
}

function Test-VisualHint {
    param(
        [string]$Content,
        [string]$Term
    )
    $index = $Content.IndexOf($Term)
    if ($index -lt 0) { return $false }
    $start = [Math]::Max(0, $index - 180)
    $end = [Math]::Min($Content.Length, $index + $Term.Length + 180)
    $window = $Content.Substring($start, $end - $start)
    $figureChar = [char]0x56FE
    $tableChar = [char]0x8868
    return ($window.IndexOf($figureChar) -ge 0 -or $window.IndexOf($tableChar) -ge 0)
}

function Test-FrontMatter {
    param(
        [object]$Chapter,
        [string]$Content
    )
    $pageEnd = 9999
    if ($null -ne $Chapter.page_end) { $pageEnd = [int]$Chapter.page_end }
    if ($pageEnd -le 25) { return $true }
    if ($pageEnd -gt 25) { return $false }
    $diChar = [string][char]0x7B2C
    $banChar = [string][char]0x7248
    $editionPattern = [regex]::Escape($diChar) + "\s*\d+\s*" + [regex]::Escape($banChar)
    $digitRunPattern = "(\d+\s+){8,}"
    $editionHits = ([regex]::Matches($Content, $editionPattern)).Count
    $digitRuns = ([regex]::Matches($Content, $digitRunPattern)).Count
    if ($editionHits -gt 8 -or $digitRuns -gt 1) { return $true }
    return $false
}

function Get-TermCount {
    param(
        [string]$Content,
        [object]$TermDef
    )
    $names = New-Object System.Collections.Generic.List[string]
    $primary = [string]$TermDef.name
    if ($primary) { $names.Add($primary) }
    foreach ($synonym in @($TermDef.synonyms)) {
        $synonymText = [string]$synonym
        if ($synonymText -and -not $names.Contains($synonymText)) {
            $names.Add($synonymText)
        }
    }
    $count = 0
    foreach ($name in $names) {
        if ($name) {
            $count += ([regex]::Matches($Content, [regex]::Escape($name))).Count
        }
    }
    return $count
}

function Get-PreferenceRank {
    param(
        [object]$Preferences,
        [string]$Category,
        [string]$BookTitle
    )
    if ($null -eq $Preferences -or -not $Category -or -not $BookTitle) { return 50 }
    $property = $Preferences.PSObject.Properties[$Category]
    if ($null -eq $property) { return 50 }
    $items = @($property.Value)
    for ($i = 0; $i -lt $items.Count; $i++) {
        if ([string]$items[$i] -eq $BookTitle) { return $i }
    }
    return 50
}

function Get-KeywordPath {
    param(
        [object]$CategoryPaths,
        [string]$Category,
        [string]$TermName
    )
    $pathItems = New-Object System.Collections.Generic.List[string]
    if ($null -ne $CategoryPaths -and $Category) {
        $property = $CategoryPaths.PSObject.Properties[$Category]
        if ($null -ne $property) {
            foreach ($item in @($property.Value)) {
                $text = [string]$item
                if ($text) { $pathItems.Add($text) }
            }
        }
    }
    if ($TermName) { $pathItems.Add($TermName) }
    return [string[]]$pathItems.ToArray()
}

function Get-SourceRef {
    param(
        [object]$Book,
        [object]$Chapter,
        [string]$Snippet
    )
    return [ordered]@{
        textbook_id = [string]$Book.textbook_id
        textbook_title = [string]$Book.title
        chapter_id = [string]$Chapter.chapter_id
        chapter_title = [string]$Chapter.title
        page_start = $Chapter.page_start
        page_end = $Chapter.page_end
        source_path = [string]$Book.source_path
        snippet = $Snippet
    }
}

function Get-VisualRef {
    param(
        [object]$Book,
        [object]$Chapter
    )
    return [ordered]@{
        textbook_id = [string]$Book.textbook_id
        textbook_title = [string]$Book.title
        chapter_id = [string]$Chapter.chapter_id
        chapter_title = [string]$Chapter.title
        page_start = $Chapter.page_start
        page_end = $Chapter.page_end
        source_path = [string]$Book.source_path
        note = "figure_or_table_hint_for_detail_index"
    }
}

function Get-RelatedTerms {
    param(
        [string]$TermName,
        [array]$RankedTerms,
        [array]$Relations,
        [int]$Limit
    )
    $relatedNames = @{}
    foreach ($relation in $Relations) {
        $source = [string]$relation.source
        $target = [string]$relation.target
        if ($source -eq $TermName -and $target) { $relatedNames[$target] = $true }
        if ($target -eq $TermName -and $source) { $relatedNames[$source] = $true }
    }
    $category = ""
    foreach ($item in $RankedTerms) {
        if ([string]$item.name -eq $TermName) {
            $category = [string]$item.category
            break
        }
    }
    $result = New-Object System.Collections.Generic.List[object]
    foreach ($item in $RankedTerms) {
        $name = [string]$item.name
        if ($name -eq $TermName) { continue }
        if ($relatedNames.ContainsKey($name) -or ([string]$item.category -eq $category)) {
            $result.Add($item)
        }
        if ($result.Count -ge $Limit) { break }
    }
    return $result
}

if (-not (Test-Path -LiteralPath $TextbooksPath)) {
    throw "Textbooks data not found: $TextbooksPath"
}
if (-not (Test-Path -LiteralPath $TermsPath)) {
    throw "Core terms file not found: $TermsPath"
}

$textbooks = Get-Content -LiteralPath $TextbooksPath -Encoding UTF8 -Raw | ConvertFrom-Json
if ($null -eq $textbooks) { $textbooks = @() }
if ($textbooks -isnot [array]) { $textbooks = @($textbooks) }
$ontology = Get-Content -LiteralPath $TermsPath -Encoding UTF8 -Raw | ConvertFrom-Json
$terms = @($ontology.terms)
$relations = @($ontology.relations)
$categoryPreferences = $ontology.category_preferences
$categoryPaths = $ontology.category_paths

$outlines = New-Object System.Collections.Generic.List[object]
$totalItems = 0
$graphCoreItems = 0
$detailItems = 0
$visualRefCount = 0

foreach ($book in $textbooks) {
    $items = New-Object System.Collections.Generic.List[object]
    $rootId = "$($book.textbook_id)_outline_root"
    $items.Add([ordered]@{
        outline_id = $rootId
        textbook_id = [string]$book.textbook_id
        parent_id = $null
        level = "book"
        order = 0
        title = [string]$book.title
        category = ""
        core_term = ""
        summary = "$($book.title)"
        keywords = @([string]$book.title)
        keyword_path = @([string]$book.title)
        page_start = 1
        page_end = $book.total_pages
        char_count = [int]$book.total_chars
        occurrence_count = 0
        importance_score = 0
        granularity = "main"
        detail_policy = "detail_index"
        source_refs = @()
        visual_refs = @()
    })
    $detailItems += 1

    $chapterOrder = 1
    foreach ($chapter in @($book.chapters)) {
        $chapterId = ("{0}_outline_ch_{1:D3}" -f [string]$book.textbook_id, $chapterOrder)
        $chapterContent = [string]$chapter.content
        $chapterSummary = Get-Snippet -Content $chapterContent -Term ""
        $isFrontMatter = Test-FrontMatter -Chapter $chapter -Content $chapterContent
        $items.Add([ordered]@{
            outline_id = $chapterId
            textbook_id = [string]$book.textbook_id
            parent_id = $rootId
            level = "chapter"
            order = $chapterOrder
            title = [string]$chapter.title
            category = ""
            core_term = ""
            summary = $chapterSummary
            keywords = @()
            keyword_path = @()
            page_start = $chapter.page_start
            page_end = $chapter.page_end
            char_count = [int]$chapter.char_count
            occurrence_count = 0
            importance_score = 0
            granularity = "main"
            detail_policy = "detail_index"
            source_refs = @((Get-SourceRef -Book $book -Chapter $chapter -Snippet $chapterSummary))
            visual_refs = @()
        })
        $detailItems += 1

        if ($isFrontMatter) {
            $chapterOrder += 1
            continue
        }

        $rankedTerms = New-Object System.Collections.Generic.List[object]
        foreach ($term in $terms) {
            $count = Get-TermCount -Content $chapterContent -TermDef $term
            if ($count -le 0) { continue }
            $priority = 0.5
            if ($null -ne $term.priority) { $priority = [double]$term.priority }
            $level = [string]$term.level
            if (-not $level) { $level = "main" }
            $category = [string]$term.category
            $preferenceRank = Get-PreferenceRank -Preferences $categoryPreferences -Category $category -BookTitle ([string]$book.title)
            $levelBoost = 0
            if ($level -eq "main") { $levelBoost = 0.18 }
            $preferenceBoost = 0
            if ($preferenceRank -lt 50) { $preferenceBoost = 0.24 - ([Math]::Min($preferenceRank, 3) * 0.04) }
            else { $preferenceBoost = -0.35 }
            $score = [Math]::Round($priority + [Math]::Min($count / 40, 0.22) + $levelBoost + $preferenceBoost, 4)
            $rankedTerms.Add([pscustomobject]@{
                name = [string]$term.name
                category = $category
                level = $level
                priority = $priority
                preference_rank = $preferenceRank
                count = $count
                score = $score
                synonyms = @($term.synonyms)
            })
        }

        $topTerms = @($rankedTerms | Sort-Object -Property @{Expression = "score"; Descending = $true}, @{Expression = "count"; Descending = $true} | Select-Object -First $MaxTermsPerChapter)
        $termOrder = 1
        foreach ($term in $topTerms) {
            $termName = [string]$term.name
            $termId = ("{0}_l1_{1:D2}" -f $chapterId, $termOrder)
            $snippet = Get-Snippet -Content $chapterContent -Term $termName
            $visualRefs = @()
            if (Test-VisualHint -Content $chapterContent -Term $termName) {
                $visualRefs = @((Get-VisualRef -Book $book -Chapter $chapter))
                $visualRefCount += 1
            }
            $detailPolicy = "graph_core"
            if ([string]$term.level -ne "main" -or [int]$term.preference_rank -ge 50) { $detailPolicy = "detail_index" }
            if ($detailPolicy -eq "graph_core") { $graphCoreItems += 1 } else { $detailItems += 1 }
            $items.Add([ordered]@{
                outline_id = $termId
                textbook_id = [string]$book.textbook_id
                parent_id = $chapterId
                level = "level1"
                order = $termOrder
                title = $termName
                category = [string]$term.category
                core_term = $termName
                summary = $snippet
                keywords = @($termName)
                keyword_path = (Get-KeywordPath -CategoryPaths $categoryPaths -Category ([string]$term.category) -TermName $termName)
                page_start = $chapter.page_start
                page_end = $chapter.page_end
                char_count = [int]$snippet.Length
                occurrence_count = [int]$term.count
                importance_score = [double]$term.score
                granularity = [string]$term.level
                detail_policy = $detailPolicy
                source_refs = @((Get-SourceRef -Book $book -Chapter $chapter -Snippet $snippet))
                visual_refs = $visualRefs
            })

            $relatedTerms = Get-RelatedTerms -TermName $termName -RankedTerms @($rankedTerms | Sort-Object -Property @{Expression = "score"; Descending = $true}, @{Expression = "count"; Descending = $true}) -Relations $relations -Limit $MaxRelatedPerTerm
            $relatedOrder = 1
            foreach ($related in $relatedTerms) {
                $relatedName = [string]$related.name
                $relatedSnippet = Get-Snippet -Content $chapterContent -Term $relatedName
                $relatedPolicy = "graph_core"
                if ([string]$related.level -ne "main" -or [int]$related.preference_rank -ge 50) { $relatedPolicy = "detail_index" }
                if ($relatedPolicy -eq "graph_core") { $graphCoreItems += 1 } else { $detailItems += 1 }
                $items.Add([ordered]@{
                    outline_id = ("{0}_l2_{1:D2}" -f $termId, $relatedOrder)
                    textbook_id = [string]$book.textbook_id
                    parent_id = $termId
                    level = "level2"
                    order = $relatedOrder
                    title = $relatedName
                    category = [string]$related.category
                    core_term = $relatedName
                    summary = $relatedSnippet
                    keywords = @($relatedName)
                    keyword_path = (Get-KeywordPath -CategoryPaths $categoryPaths -Category ([string]$related.category) -TermName $relatedName)
                    page_start = $chapter.page_start
                    page_end = $chapter.page_end
                    char_count = [int]$relatedSnippet.Length
                    occurrence_count = [int]$related.count
                    importance_score = [double]$related.score
                    granularity = [string]$related.level
                    detail_policy = $relatedPolicy
                    source_refs = @((Get-SourceRef -Book $book -Chapter $chapter -Snippet $relatedSnippet))
                    visual_refs = @()
                })
                $relatedOrder += 1
            }
            $termOrder += 1
        }
        $chapterOrder += 1
    }

    $outline = [ordered]@{
        textbook_id = [string]$book.textbook_id
        textbook_title = [string]$book.title
        source_path = [string]$book.source_path
        total_chars = [int]$book.total_chars
        item_count = [int]$items.Count
        items = $items
    }
    $outlines.Add($outline)
    $totalItems += $items.Count
}

$summary = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    source_textbooks = [int]$textbooks.Count
    outline_count = [int]$outlines.Count
    item_count = [int]$totalItems
    graph_core_items = [int]$graphCoreItems
    detail_index_items = [int]$detailItems
    visual_ref_count = [int]$visualRefCount
    demo_output = $DemoOutputPath
    runtime_output = $RuntimeOutputPath
}

New-DirectoryForFile -PathValue $DemoOutputPath
New-DirectoryForFile -PathValue $RuntimeOutputPath
New-DirectoryForFile -PathValue $SummaryPath
New-DirectoryForFile -PathValue $ReportPath
$outlines | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $DemoOutputPath -Encoding UTF8
$outlines | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $RuntimeOutputPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryPath -Encoding UTF8

$bookRows = foreach ($outline in $outlines) {
    "| $($outline.textbook_id) | $($outline.textbook_title) | $($outline.item_count) |"
}

$reportLines = New-Object System.Collections.Generic.List[string]
$reportLines.Add("# Outline Build Check")
$reportLines.Add("")
$reportLines.Add("Generated at: $($summary.generated_at)")
$reportLines.Add("")
$reportLines.Add("## Outputs")
$reportLines.Add("")
$reportLines.Add("| Item | Path |")
$reportLines.Add("|---|---|")
$reportLines.Add("| Demo outlines | $DemoOutputPath |")
$reportLines.Add("| Runtime outlines | $RuntimeOutputPath |")
$reportLines.Add("| Summary | $SummaryPath |")
$reportLines.Add("")
$reportLines.Add("## Metrics")
$reportLines.Add("")
$reportLines.Add("| Metric | Value |")
$reportLines.Add("|---|---:|")
$reportLines.Add("| Textbooks | $($summary.source_textbooks) |")
$reportLines.Add("| Outline items | $($summary.item_count) |")
$reportLines.Add("| Graph-core items | $($summary.graph_core_items) |")
$reportLines.Add("| Detail-index items | $($summary.detail_index_items) |")
$reportLines.Add("| Visual refs | $($summary.visual_ref_count) |")
$reportLines.Add("")
$reportLines.Add("## Book Outline Counts")
$reportLines.Add("")
$reportLines.Add("| ID | Textbook | Items |")
$reportLines.Add("|---|---|---:|")
foreach ($row in $bookRows) { $reportLines.Add($row) }
$reportLines.Add("")
$reportLines.Add("## Why This Layer Exists")
$reportLines.Add("")
$reportLines.Add("- Step 1 is pure data processing: textbook -> chapter -> level1/level2 knowledge outline.")
$reportLines.Add("- Step 2 graph generation consumes only graph_core outline items, while detail_index items stay searchable.")
$reportLines.Add("- Figure/table hints are preserved as visual_refs instead of being collapsed into text deduplication.")
$report = $reportLines -join "`r`n"
$report | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host "Outlines: $($outlines.Count)"
Write-Host "Items: $totalItems"
Write-Host "Graph-core items: $graphCoreItems"
Write-Host "Detail-index items: $detailItems"
Write-Host "Visual refs: $visualRefCount"
Write-Host "Wrote runtime outlines: $RuntimeOutputPath"
