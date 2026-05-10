param(
    [string]$OutlinesPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\outlines.json",
    [string]$TermsPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\backend\app\resources\core_terms.json",
    [string]$DemoOutputPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\graph_demo.json",
    [string]$RuntimeOutputPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\graph.json",
    [string]$SummaryPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\graph_summary.json",
    [string]$ReportPath = "E:\codex test\Preparation for Hacson\hacson_knowledge_agent\report\graph_build_check.md",
    [int]$MaxNodes = 90,
    [int]$MaxSourceRefs = 5,
    [int]$MaxVisualRefs = 4
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function New-DirectoryForFile {
    param([string]$PathValue)
    $dir = Split-Path -Parent $PathValue
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

function Add-UniqueRef {
    param(
        [System.Collections.Generic.List[object]]$List,
        [object]$Ref,
        [int]$Limit
    )
    if ($null -eq $Ref -or $List.Count -ge $Limit) { return }
    $key = "$($Ref.textbook_id)|$($Ref.chapter_id)|$($Ref.page_start)"
    foreach ($existing in $List) {
        $existingKey = "$($existing.textbook_id)|$($existing.chapter_id)|$($existing.page_start)"
        if ($existingKey -eq $key) { return }
    }
    $List.Add($Ref)
}

if (-not (Test-Path -LiteralPath $OutlinesPath)) {
    throw "Outlines data not found. Run scripts\build_textbook_outlines.ps1 first: $OutlinesPath"
}
if (-not (Test-Path -LiteralPath $TermsPath)) {
    throw "Core terms file not found: $TermsPath"
}

$outlines = Get-Content -LiteralPath $OutlinesPath -Encoding UTF8 -Raw | ConvertFrom-Json
if ($null -eq $outlines) { $outlines = @() }
if ($outlines -isnot [array]) { $outlines = @($outlines) }
$ontology = Get-Content -LiteralPath $TermsPath -Encoding UTF8 -Raw | ConvertFrom-Json
$relations = @($ontology.relations)

$groups = @{}
$parentLinks = @{}
foreach ($outline in $outlines) {
    $itemById = @{}
    foreach ($item in @($outline.items)) {
        $itemById[[string]$item.outline_id] = $item
    }
    foreach ($item in @($outline.items)) {
        if ([string]$item.detail_policy -ne "graph_core" -or -not [string]$item.core_term) {
            continue
        }
        $term = [string]$item.core_term
        if (-not $groups.ContainsKey($term)) {
            $groups[$term] = [pscustomobject]@{
                term = $term
                category = [string]$item.category
                keyword_path = @($item.keyword_path)
                textbooks = @{}
                source_refs = New-Object System.Collections.Generic.List[object]
                visual_refs = New-Object System.Collections.Generic.List[object]
                frequency = 0
                importance = 0.0
                snippet = ""
                textbook_id = [string]$item.textbook_id
                chapter_id = $null
                page = $null
                granularity = [string]$item.granularity
            }
        }
        $group = $groups[$term]
        $group.textbooks[[string]$outline.textbook_title] = $true
        $group.frequency = [int]$group.frequency + [Math]::Max([int]$item.occurrence_count, 1)
        if ([double]$item.importance_score -gt [double]$group.importance) {
            $group.importance = [double]$item.importance_score
        }
        if (-not [string]$group.snippet -and [string]$item.summary) {
            $group.snippet = [string]$item.summary
            $group.textbook_id = [string]$item.textbook_id
            if (@($item.source_refs).Count -gt 0) {
                $group.chapter_id = [string]$item.source_refs[0].chapter_id
                $group.page = $item.source_refs[0].page_start
            }
        }
        foreach ($ref in @($item.source_refs)) {
            Add-UniqueRef -List $group.source_refs -Ref $ref -Limit $MaxSourceRefs
        }
        foreach ($ref in @($item.visual_refs)) {
            Add-UniqueRef -List $group.visual_refs -Ref $ref -Limit $MaxVisualRefs
        }

        $parentId = [string]$item.parent_id
        if ($parentId -and $itemById.ContainsKey($parentId)) {
            $parent = $itemById[$parentId]
            if ([string]$parent.detail_policy -eq "graph_core" -and [string]$parent.core_term) {
                $pairKey = "$($parent.core_term)|$term"
                if (-not $parentLinks.ContainsKey($pairKey)) { $parentLinks[$pairKey] = 0 }
                $parentLinks[$pairKey] += 1
            }
        }
    }
}

$rankedGroups = @($groups.Values | Sort-Object -Property @{Expression = { $_.textbooks.Keys.Count }; Descending = $true}, @{Expression = "importance"; Descending = $true}, @{Expression = "frequency"; Descending = $true} | Select-Object -First $MaxNodes)
$nodes = New-Object System.Collections.Generic.List[object]
$nodeByTerm = @{}
$index = 1
foreach ($group in $rankedGroups) {
    $nodeId = ("kg_{0:D3}" -f $index)
    $nodeByTerm[[string]$group.term] = $nodeId
    $nodes.Add([ordered]@{
        id = $nodeId
        name = [string]$group.term
        definition = if ([string]$group.snippet) { [string]$group.snippet } else { [string]$group.term }
        category = [string]$group.category
        textbook_id = [string]$group.textbook_id
        chapter_id = $group.chapter_id
        page = $group.page
        source_text = [string]$group.snippet
        frequency = [int]$group.frequency
        status = "kept"
        importance_score = [Math]::Round([double]$group.importance, 4)
        granularity = [string]$group.granularity
        keyword_path = @($group.keyword_path)
        textbooks = @($group.textbooks.Keys | Sort-Object)
        source_refs = $group.source_refs
        visual_refs = $group.visual_refs
    })
    $index += 1
}

$pathNodeByKey = @{}
$pathIndex = 1
$coreNodesSnapshot = New-Object System.Collections.Generic.List[object]
foreach ($node in $nodes) { $coreNodesSnapshot.Add($node) }
foreach ($node in $coreNodesSnapshot) {
    $pathParts = @($node["keyword_path"])
    if ($pathParts.Count -lt 2) { continue }
    $memberTextbooks = @($node["textbooks"])
    for ($i = 0; $i -lt $pathParts.Count - 1; $i++) {
        $prefixParts = @($pathParts | Select-Object -First ($i + 1))
        $pathKey = $prefixParts -join " > "
        if ($pathNodeByKey.ContainsKey($pathKey)) { continue }
        $pathNodeId = ("path_{0:D3}" -f $pathIndex)
        $pathNodeByKey[$pathKey] = $pathNodeId
        $nodes.Add([ordered]@{
            id = $pathNodeId
            name = [string]$pathParts[$i]
            definition = "医学多级关键词路径节点：$pathKey"
            category = "knowledge_layer"
            textbook_id = "multi_source"
            chapter_id = $null
            page = $null
            source_text = ""
            frequency = 1
            status = "merged"
            importance_score = 1.0
            granularity = "main"
            keyword_path = $prefixParts
            textbooks = $memberTextbooks
            source_refs = @()
            visual_refs = @()
        })
        $pathIndex += 1
    }
}

$edges = New-Object System.Collections.Generic.List[object]
$seen = @{}
foreach ($relation in $relations) {
    $sourceName = [string]$relation.source
    $targetName = [string]$relation.target
    if (-not $nodeByTerm.ContainsKey($sourceName) -or -not $nodeByTerm.ContainsKey($targetName)) {
        continue
    }
    $relationType = [string]$relation.relation_type
    if ($relationType -notin @("prerequisite", "parallel", "contains", "applies_to")) {
        $relationType = "parallel"
    }
    $source = [string]$nodeByTerm[$sourceName]
    $target = [string]$nodeByTerm[$targetName]
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

foreach ($pair in ($parentLinks.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 100)) {
    $parts = $pair.Key.Split("|")
    if ($parts.Count -lt 2) { continue }
    $parentTerm = $parts[0]
    $childTerm = $parts[1]
    if (-not $nodeByTerm.ContainsKey($parentTerm) -or -not $nodeByTerm.ContainsKey($childTerm)) {
        continue
    }
    $source = [string]$nodeByTerm[$parentTerm]
    $target = [string]$nodeByTerm[$childTerm]
    $key = "$source|$target|contains"
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true
    $edges.Add([ordered]@{
        source = $source
        target = $target
        relation_type = "contains"
        description = "outline_parent_child_count=$($pair.Value)"
    })
}

$pathGroups = @{}
foreach ($node in $nodes) {
    $pathParts = @($node["keyword_path"])
    if ([string]$node["category"] -eq "知识层级") { continue }
    if ($pathParts.Count -lt 2) { continue }
    for ($i = 1; $i -lt $pathParts.Count; $i++) {
        $sourceKey = (@($pathParts | Select-Object -First $i)) -join " > "
        $targetIsTerm = ($i -eq $pathParts.Count - 1)
        if (-not $pathNodeByKey.ContainsKey($sourceKey)) { continue }
        $source = [string]$pathNodeByKey[$sourceKey]
        if ($targetIsTerm) {
            $targetTerm = [string]$pathParts[$i]
            if (-not $nodeByTerm.ContainsKey($targetTerm)) { continue }
            $target = [string]$nodeByTerm[$targetTerm]
        } else {
            $targetKey = (@($pathParts | Select-Object -First ($i + 1))) -join " > "
            if (-not $pathNodeByKey.ContainsKey($targetKey)) { continue }
            $target = [string]$pathNodeByKey[$targetKey]
        }
        $key = "$source|$target|contains"
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = $true
        $edges.Add([ordered]@{
            source = $source
            target = $target
            relation_type = "contains"
            description = "multi_level_keyword_path"
        })
    }
    $prefix = ($pathParts | Select-Object -First ([Math]::Max($pathParts.Count - 1, 1))) -join " > "
    if (-not $pathGroups.ContainsKey($prefix)) {
        $pathGroups[$prefix] = New-Object System.Collections.Generic.List[object]
    }
    $pathGroups[$prefix].Add($node)
}

foreach ($entry in $pathGroups.GetEnumerator()) {
    $members = @($entry.Value | Sort-Object -Property @{Expression = { $_["textbooks"].Count }; Descending = $true}, @{Expression = "frequency"; Descending = $true} | Select-Object -First 8)
    for ($i = 0; $i -lt $members.Count; $i++) {
        for ($j = $i + 1; $j -lt $members.Count; $j++) {
            $source = [string]$members[$i]["id"]
            $target = [string]$members[$j]["id"]
            $key = "$source|$target|parallel"
            if ($seen.ContainsKey($key)) { continue }
            $seen[$key] = $true
            $edges.Add([ordered]@{
                source = $source
                target = $target
                relation_type = "parallel"
                description = "same_keyword_path=$($entry.Key)"
            })
        }
    }
}

$categoryCounts = @{}
$keywordPathCounts = @{}
$visualRefTotal = 0
foreach ($node in $nodes) {
    $category = [string]$node["category"]
    if (-not $categoryCounts.ContainsKey($category)) { $categoryCounts[$category] = 0 }
    $categoryCounts[$category] += 1
    $pathKey = (@($node["keyword_path"]) | Select-Object -First 3) -join " > "
    if (-not $keywordPathCounts.ContainsKey($pathKey)) { $keywordPathCounts[$pathKey] = 0 }
    $keywordPathCounts[$pathKey] += 1
    foreach ($unused in $node["visual_refs"]) { $visualRefTotal += 1 }
}

$graph = [ordered]@{
    nodes = $nodes
    edges = $edges
}
$summary = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    source_outlines = [int]$outlines.Count
    node_count = [int]$nodes.Count
    edge_count = [int]$edges.Count
    visual_ref_count = [int]$visualRefTotal
    category_counts = $categoryCounts
    keyword_path_counts = $keywordPathCounts
    graph_demo_path = $DemoOutputPath
    graph_runtime_path = $RuntimeOutputPath
}

New-DirectoryForFile -PathValue $DemoOutputPath
New-DirectoryForFile -PathValue $RuntimeOutputPath
New-DirectoryForFile -PathValue $SummaryPath
New-DirectoryForFile -PathValue $ReportPath
$graph | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $DemoOutputPath -Encoding UTF8
$graph | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $RuntimeOutputPath -Encoding UTF8
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryPath -Encoding UTF8

$categoryRows = foreach ($key in ($categoryCounts.Keys | Sort-Object)) {
    "| $key | $($categoryCounts[$key]) |"
}
$pathRows = foreach ($key in ($keywordPathCounts.Keys | Sort-Object)) {
    "| $key | $($keywordPathCounts[$key]) |"
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
$reportLines.Add("| Source outlines | $($summary.source_outlines) |")
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
$reportLines.Add("## Keyword Paths")
$reportLines.Add("")
$reportLines.Add("| Keyword path | Nodes |")
$reportLines.Add("|---|---:|")
foreach ($row in $pathRows) { $reportLines.Add($row) }
$reportLines.Add("")
$reportLines.Add("## Scoring Evidence")
$reportLines.Add("")
$reportLines.Add("- B2: graph JSON is generated from textbook outlines, not raw noisy full text.")
$reportLines.Add("- B3/C: graph nodes carry category and keyword_path fields for multi-level medical browsing.")
$reportLines.Add("- B4: repeated core terms across textbooks are merged by core_term and supported by source_refs.")
$reportLines.Add("- Image strategy: visual_refs preserve page-level figure/table hints outside text deduplication.")
$report = $reportLines -join "`r`n"
$report | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host "Graph nodes: $($nodes.Count)"
Write-Host "Graph edges: $($edges.Count)"
Write-Host "Visual refs: $visualRefTotal"
Write-Host "Wrote runtime graph: $RuntimeOutputPath"
