param(
    [string]$TextbooksPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\textbooks.json",
    [string]$TermsPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\backend\app\resources\core_terms.json",
    [string]$DemoOutputPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\graph_demo.json",
    [string]$RuntimeOutputPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\graph.json",
    [string]$SummaryPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\graph_summary.json",
    [string]$ReportPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\report\graph_build_check.md",
    [int]$MaxNodes = 90,
    [int]$MaxRefsPerNode = 5,
    [int]$MaxVisualRefsPerNode = 4,
    [int]$MaxCooccurrenceEdges = 140
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
    if ($index -lt 0) { return "" }
    $start = [Math]::Max(0, $index - $Radius)
    $end = [Math]::Min($Content.Length, $index + $Term.Length + $Radius)
    $length = $end - $start
    if ($length -le 0) { return "" }
    $snippet = $Content.Substring($start, $length)
    $snippet = [regex]::Replace($snippet, "\s+", " ").Trim()
    if ($snippet.Length -gt 220) {
        return $snippet.Substring(0, 220)
    }
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

function Test-SnippetQuality {
    param([string]$Snippet)
    if (-not $Snippet) { return $false }
    if ($Snippet.Length -lt 20) { return $false }
    $digitCount = ([regex]::Matches($Snippet, "\d")).Count
    if ($digitCount -gt 35) { return $false }
    if ($Snippet -match "(\d+\s+){8,}") { return $false }
    return $true
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

$candidates = New-Object System.Collections.Generic.List[object]
$termIndex = 1
foreach ($termDef in $terms) {
    $primaryName = [string]$termDef.name
    if (-not $primaryName) { continue }
    $names = New-Object System.Collections.Generic.List[string]
    $names.Add($primaryName)
    foreach ($synonym in @($termDef.synonyms)) {
        $synonymText = [string]$synonym
        if ($synonymText -and -not $names.Contains($synonymText)) {
            $names.Add($synonymText)
        }
    }

    $candidateRefs = New-Object System.Collections.Generic.List[object]
    $candidateVisualRefs = New-Object System.Collections.Generic.List[object]
    $titleSet = @{}
    $frequency = 0
    $firstTextbookId = "multi_source"
    $firstChapterId = $null
    $firstPage = $null

    foreach ($book in $textbooks) {
        foreach ($chapter in @($book.chapters)) {
            $chapterText = [string]$chapter.content
            $chapterTitle = [string]$chapter.title
            $matchedNames = New-Object System.Collections.Generic.List[string]
            foreach ($name in $names) {
                if ($chapterText.Contains($name) -or $chapterTitle.Contains($name)) {
                    $matchedNames.Add($name)
                }
            }
            if ($matchedNames.Count -eq 0) { continue }

            $matchedFrequency = 0
            foreach ($name in $matchedNames) {
                $matchedFrequency += ([regex]::Matches($chapterText, [regex]::Escape($name))).Count
            }
            if ($matchedFrequency -le 0) { $matchedFrequency = 1 }
            $frequency += $matchedFrequency
            $titleSet[[string]$book.title] = $true

            if ($firstTextbookId -eq "multi_source") {
                $firstTextbookId = [string]$book.textbook_id
                $firstChapterId = [string]$chapter.chapter_id
                $firstPage = $chapter.page_start
            }

            $firstMatch = [string]$matchedNames[0]
            $snippet = Get-Snippet -Content $chapterText -Term $firstMatch
            if (Test-SnippetQuality -Snippet $snippet) {
                $preferenceRank = Get-PreferenceRank -Preferences $categoryPreferences -Category ([string]$termDef.category) -BookTitle ([string]$book.title)
                $candidateRefs.Add([pscustomobject]@{
                    rank = $preferenceRank
                    page = if ($null -ne $chapter.page_start) { [int]$chapter.page_start } else { 9999 }
                    ref = [ordered]@{
                        textbook_id = [string]$book.textbook_id
                        textbook_title = [string]$book.title
                        chapter_id = [string]$chapter.chapter_id
                        chapter_title = [string]$chapter.title
                        page_start = $chapter.page_start
                        page_end = $chapter.page_end
                        source_path = [string]$book.source_path
                        snippet = $snippet
                    }
                })
            }
            if (Test-VisualHint -Content $chapterText -Term $firstMatch) {
                $preferenceRankForVisual = Get-PreferenceRank -Preferences $categoryPreferences -Category ([string]$termDef.category) -BookTitle ([string]$book.title)
                $candidateVisualRefs.Add([pscustomobject]@{
                    rank = $preferenceRankForVisual
                    page = if ($null -ne $chapter.page_start) { [int]$chapter.page_start } else { 9999 }
                    ref = [ordered]@{
                        textbook_id = [string]$book.textbook_id
                        textbook_title = [string]$book.title
                        chapter_id = [string]$chapter.chapter_id
                        chapter_title = [string]$chapter.title
                        page_start = $chapter.page_start
                        page_end = $chapter.page_end
                        source_path = [string]$book.source_path
                        note = "figure_or_table_hint_near_concept"
                    }
                })
            }
        }
    }

    if ($frequency -le 0) {
        $termIndex += 1
        continue
    }

    $priority = 0.5
    if ($null -ne $termDef.priority) { $priority = [double]$termDef.priority }
    $coverage = 0
    if ($textbooks.Count -gt 0) { $coverage = [double]$titleSet.Keys.Count / [double]$textbooks.Count }
    $freqScore = [Math]::Log(1 + $frequency) / 8
    if ($freqScore -gt 1) { $freqScore = 1 }
    $importance = [Math]::Round(($priority * 0.7) + ($freqScore * 0.15) + ($coverage * 0.15), 4)
    $level = [string]$termDef.level
    if (-not $level) { $level = "main" }
    $levelBoost = 0
    if ($level -eq "main") { $levelBoost = 1 }
    $refs = @($candidateRefs | Sort-Object -Property @{Expression = "rank"; Descending = $false}, @{Expression = "page"; Descending = $false} | Select-Object -First $MaxRefsPerNode | ForEach-Object { $_.ref })
    $visualRefs = @($candidateVisualRefs | Sort-Object -Property @{Expression = "rank"; Descending = $false}, @{Expression = "page"; Descending = $false} | Select-Object -First $MaxVisualRefsPerNode | ForEach-Object { $_.ref })
    $sourceText = ""
    if ($refs.Count -gt 0) { $sourceText = [string]$refs[0].snippet }
    $nodeTextbookId = $firstTextbookId
    $nodeChapterId = $firstChapterId
    $nodePage = $firstPage
    if ($refs.Count -gt 0) {
        $nodeTextbookId = [string]$refs[0].textbook_id
        $nodeChapterId = [string]$refs[0].chapter_id
        $nodePage = $refs[0].page_start
    }
    $definition = $sourceText
    if (-not $definition) { $definition = $primaryName }

    $node = [ordered]@{
        id = ("kg_{0:D3}" -f $termIndex)
        name = $primaryName
        definition = $definition
        category = [string]$termDef.category
        textbook_id = $nodeTextbookId
        chapter_id = $nodeChapterId
        page = $nodePage
        source_text = $sourceText
        frequency = [int]$frequency
        status = "kept"
        importance_score = $importance
        granularity = $level
        textbooks = @($titleSet.Keys | Sort-Object)
        source_refs = $refs
        visual_refs = $visualRefs
    }
    $candidates.Add([pscustomobject]@{
        sort_score = $importance + $levelBoost
        frequency = $frequency
        node = $node
    })
    $termIndex += 1
}

$nodes = @($candidates | Sort-Object -Property @{Expression = "sort_score"; Descending = $true}, @{Expression = "frequency"; Descending = $true} | Select-Object -First $MaxNodes | ForEach-Object { $_.node })
$nodeByName = @{}
foreach ($node in $nodes) {
    $nodeByName[[string]$node.name] = $node
}

$edges = New-Object System.Collections.Generic.List[object]
$seen = @{}
foreach ($relation in $relations) {
    $sourceName = [string]$relation.source
    $targetName = [string]$relation.target
    if (-not $nodeByName.ContainsKey($sourceName) -or -not $nodeByName.ContainsKey($targetName)) {
        continue
    }
    $source = [string]$nodeByName[$sourceName].id
    $target = [string]$nodeByName[$targetName].id
    $relationType = [string]$relation.relation_type
    if ($relationType -notin @("prerequisite", "parallel", "contains", "applies_to")) {
        $relationType = "parallel"
    }
    $key = "$source|$target|$relationType"
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true
    $edges.Add([ordered]@{
        source = $source
        target = $target
        relation_type = $relationType
        description = [string]$relation.description
    })
}

$termNames = @($nodes | ForEach-Object { [string]$_.name })
$pairCounts = @{}
foreach ($book in $textbooks) {
    foreach ($chapter in @($book.chapters)) {
        $content = [string]$chapter.content
        $present = New-Object System.Collections.Generic.List[string]
        foreach ($name in $termNames) {
            if ($content.Contains($name)) {
                $present.Add($name)
            }
            if ($present.Count -ge 10) { break }
        }
        for ($i = 0; $i -lt $present.Count; $i++) {
            for ($j = $i + 1; $j -lt $present.Count; $j++) {
                $left = [string]$nodeByName[$present[$i]].id
                $right = [string]$nodeByName[$present[$j]].id
                if ([string]::Compare($left, $right) -gt 0) {
                    $tmp = $left
                    $left = $right
                    $right = $tmp
                }
                $pairKey = "$left|$right"
                if (-not $pairCounts.ContainsKey($pairKey)) { $pairCounts[$pairKey] = 0 }
                $pairCounts[$pairKey] += 1
            }
        }
    }
}

$coCount = 0
foreach ($pair in ($pairCounts.GetEnumerator() | Sort-Object -Property Value -Descending)) {
    if ($coCount -ge $MaxCooccurrenceEdges) { break }
    $parts = $pair.Key.Split("|")
    $source = $parts[0]
    $target = $parts[1]
    $key = "$source|$target|parallel"
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true
    $edges.Add([ordered]@{
        source = $source
        target = $target
        relation_type = "parallel"
        description = "same_chapter_cooccurrence_count=$($pair.Value)"
    })
    $coCount += 1
}

$graph = [ordered]@{
    nodes = $nodes
    edges = $edges
}

$categoryCounts = @{}
$visualRefTotal = 0
foreach ($node in $nodes) {
    $category = [string]$node["category"]
    if (-not $categoryCounts.ContainsKey($category)) { $categoryCounts[$category] = 0 }
    $categoryCounts[$category] += 1
    $visualRefCountForNode = 0
    $visualRefItems = $node["visual_refs"]
    foreach ($unused in $visualRefItems) {
        $visualRefCountForNode += 1
    }
    $visualRefTotal = [int]$visualRefTotal + [int]$visualRefCountForNode
}

$summary = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    source_textbooks = [int]$textbooks.Count
    node_count = [int]$nodes.Count
    edge_count = [int]$edges.Count
    visual_ref_count = [int]$visualRefTotal
    max_nodes = [int]$MaxNodes
    graph_demo_path = $DemoOutputPath
    graph_runtime_path = $RuntimeOutputPath
    category_counts = $categoryCounts
}

New-DirectoryForFile -PathValue $DemoOutputPath
New-DirectoryForFile -PathValue $RuntimeOutputPath
New-DirectoryForFile -PathValue $SummaryPath
New-DirectoryForFile -PathValue $ReportPath
$graph | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $DemoOutputPath -Encoding UTF8
$graph | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $RuntimeOutputPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryPath -Encoding UTF8

$categoryRows = foreach ($key in ($categoryCounts.Keys | Sort-Object)) {
    "| $key | $($categoryCounts[$key]) |"
}

$reportLines = New-Object System.Collections.Generic.List[string]
$reportLines.Add("# Graph Build Check")
$reportLines.Add("")
$reportLines.Add("Generated at: $($summary.generated_at)")
$reportLines.Add("")
$reportLines.Add("## Outputs")
$reportLines.Add("")
$reportLines.Add("| Item | Path |")
$reportLines.Add("|---|---|")
$reportLines.Add("| Demo graph | $DemoOutputPath |")
$reportLines.Add("| Runtime graph | $RuntimeOutputPath |")
$reportLines.Add("| Summary | $SummaryPath |")
$reportLines.Add("")
$reportLines.Add("## Metrics")
$reportLines.Add("")
$reportLines.Add("| Metric | Value |")
$reportLines.Add("|---|---:|")
$reportLines.Add("| Textbooks | $($summary.source_textbooks) |")
$reportLines.Add("| Nodes | $($summary.node_count) |")
$reportLines.Add("| Edges | $($summary.edge_count) |")
$reportLines.Add("| Visual refs | $($summary.visual_ref_count) |")
$reportLines.Add("")
$reportLines.Add("## Categories")
$reportLines.Add("")
$reportLines.Add("| Category | Nodes |")
$reportLines.Add("|---|---:|")
foreach ($row in $categoryRows) { $reportLines.Add($row) }
$reportLines.Add("")
$reportLines.Add("## Scoring Evidence")
$reportLines.Add("")
$reportLines.Add("- B2: graph JSON is generated from parsed textbooks with node schema, relation schema, and source snippets.")
$reportLines.Add("- B3/C: graph_demo.json can be loaded as a saved demo while graph.json supports runtime generation.")
$reportLines.Add("- B4: nodes preserve granularity and source refs, preparing merge/keep/remove decisions.")
$reportLines.Add("- Image strategy: visual_refs keep page-level figure/table hints and original PDF paths for later image extraction.")
$report = $reportLines -join "`r`n"
$report | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host "Graph nodes: $($nodes.Count)"
Write-Host "Graph edges: $($edges.Count)"
Write-Host "Visual refs: $visualRefTotal"
Write-Host "Wrote demo graph: $DemoOutputPath"
Write-Host "Wrote runtime graph: $RuntimeOutputPath"
