# Adam Framework — Ingest Triples (Step 2 of 2)
# Loads extracted facts from legacy_importer.py into your neural memory graph.
#
# Prerequisites:
#   - neural-memory MCP server running (listed in mcporter.json)
#   - mcporter installed and in PATH
#   - extracted_triples.json exists (run legacy_importer.py first)
#
# Usage:
#   .\ingest_triples.ps1 -VaultPath "C:\YourVault"
#   .\ingest_triples.ps1 -VaultPath "C:\YourVault" -DryRun
#   .\ingest_triples.ps1 -VaultPath "C:\YourVault" -StartAt 150
#
# Options:
#   -VaultPath   Path to your Vault directory (required)
#   -DryRun      Show what would be ingested without actually running mcporter
#   -StartAt     Resume from a specific fact number (if a previous run was interrupted)
#   -DelayMs     Milliseconds between calls (default: 80 — safe for most systems)

param(
    [Parameter(Mandatory=$true)]
    [string]$VaultPath,

    [switch]$DryRun,

    [int]$StartAt = 0,

    [int]$DelayMs = 80
)

$ErrorActionPreference = "Continue"

# ── PATHS ─────────────────────────────────────────────────────────────────────
$TriplesPath = Join-Path $VaultPath "imports\extracted_triples.json"
$LogPath     = Join-Path $VaultPath "imports\ingest_log.txt"

# ── PREFLIGHT ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== ADAM FRAMEWORK — NEURAL MEMORY INGEST ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $TriplesPath)) {
    Write-Host "ERROR: extracted_triples.json not found at:" -ForegroundColor Red
    Write-Host "  $TriplesPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Run legacy_importer.py first to generate this file." -ForegroundColor Yellow
    exit 1
}

# Check mcporter is available
$mcporterCheck = Get-Command mcporter -ErrorAction SilentlyContinue
if (-not $mcporterCheck) {
    Write-Host "ERROR: mcporter not found in PATH." -ForegroundColor Red
    Write-Host "Make sure mcporter is installed and your OpenClaw gateway is running." -ForegroundColor Yellow
    exit 1
}

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
Write-Host "Loading $TriplesPath..." -ForegroundColor Gray
$data    = Get-Content $TriplesPath -Raw -Encoding UTF8 | ConvertFrom-Json
$triples = $data.facts
$total   = $triples.Count

if ($total -eq 0) {
    Write-Host "No facts found in extracted_triples.json. Nothing to ingest." -ForegroundColor Yellow
    exit 0
}

$meta = $data._meta
if ($meta) {
    Write-Host "  Source:    $($meta.source)" -ForegroundColor Gray
    Write-Host "  Extracted: $($meta.generated)" -ForegroundColor Gray
    Write-Host "  User name: $($meta.user_name)" -ForegroundColor Gray
}

Write-Host ""
if ($DryRun) {
    Write-Host "DRY RUN MODE — no mcporter calls will be made" -ForegroundColor Yellow
    Write-Host ""
}

$startIdx   = [Math]::Max(0, $StartAt)
$remaining  = $total - $startIdx
$estMinutes = [Math]::Max(1, [Math]::Round($remaining * ($DelayMs + 4350) / 60000))

Write-Host "Facts to ingest: $remaining of $total" -ForegroundColor White
if ($startIdx -gt 0) {
    Write-Host "Resuming from:   fact #$($startIdx + 1)" -ForegroundColor Yellow
}
Write-Host "Estimated time:  ~$estMinutes minutes" -ForegroundColor White
Write-Host "Delay per call:  ${DelayMs}ms" -ForegroundColor Gray
Write-Host ""
Write-Host "The ingest runs in the background. You can use your AI normally." -ForegroundColor Gray
Write-Host "Do not close this window until complete." -ForegroundColor Gray
Write-Host ""

# ── LOG HEADER ────────────────────────────────────────────────────────────────
$runStart = Get-Date
$logHeader = @"
=== Ingest Run: $($runStart.ToString('yyyy-MM-dd HH:mm:ss')) ===
Source: $TriplesPath
Total facts: $total
Starting at: $startIdx
Dry run: $DryRun
"@
Add-Content -Path $LogPath -Value $logHeader -Encoding UTF8

# ── INGEST LOOP ───────────────────────────────────────────────────────────────
$success = 0
$fail    = 0
$skip    = 0
$errors  = @()

for ($i = $startIdx; $i -lt $total; $i++) {
    $triple = $triples[$i]

    # Triples are stored as arrays: [subject, predicate, object]
    if ($triple -is [System.Array] -or $triple.PSObject.Properties.Name -contains 'Count') {
        $subj  = $triple[0]
        $pred  = $triple[1]
        $obj   = $triple[2]
    } else {
        # Fallback for object format
        $subj  = $triple.subject
        $pred  = $triple.predicate
        $obj   = $triple.object
    }

    # Skip empty or malformed triples
    if (-not $subj -or -not $obj -or $obj.Length -lt 3) {
        $skip++
        continue
    }

    # Build content string — replace pipe chars that break shell (Bug #2 from incident report)
    $content = "$subj - $pred - $obj"

    # Escape single quotes for mcporter call syntax (Bug #1 fix)
    $escaped = $content -replace "'", "''"

    $cmd = "neural-memory.nmem_remember(content: '$escaped', type: 'fact', priority: 5, tags: ['legacy_import', 'ai_export'])"

    if ($DryRun) {
        Write-Host "  [DRY RUN] $($i+1)/$total — $($content.Substring(0, [Math]::Min(70, $content.Length)))" -ForegroundColor DarkGray
        $success++
    } else {
        try {
            $result = (mcporter call $cmd 2>&1) | Out-String

            if ($result -match '"success":\s*true' -or $result -match '"stored"' -or $result -match '"id"') {
                $success++
                if ($success % 50 -eq 0) {
                    $pct = [Math]::Round(($i + 1) / $total * 100)
                    $elapsed = ((Get-Date) - $runStart).TotalMinutes
                    $rate = if ($elapsed -gt 0) { [Math]::Round($success / $elapsed) } else { 0 }
                    Write-Host "  [$success/$total — $pct%] $rate facts/min" -ForegroundColor Green
                }
            } else {
                $fail++
                $errMsg = "FAIL [$($i+1)]: $($content.Substring(0, [Math]::Min(60, $content.Length)))"
                if ($errors.Count -le 5) {
                    Write-Host "  $errMsg" -ForegroundColor Red
                    if ($result.Trim()) {
                        Write-Host "    Response: $($result.Trim().Substring(0, [Math]::Min(120, $result.Trim().Length)))" -ForegroundColor DarkRed
                    }
                }
                $errors += $errMsg
                Add-Content -Path $LogPath -Value $errMsg -Encoding UTF8
            }
        } catch {
            $fail++
            $errMsg = "ERR [$($i+1)]: $_"
            if ($errors.Count -le 5) { Write-Host "  $errMsg" -ForegroundColor Red }
            $errors += $errMsg
            Add-Content -Path $LogPath -Value $errMsg -Encoding UTF8
        }
    }

    # Abort early if something is clearly broken (no successes after 20 tries)
    if ($fail -gt 20 -and $success -eq 0) {
        Write-Host ""
        Write-Host "ABORT: 20+ failures with 0 successes." -ForegroundColor Red
        Write-Host "Check that your neural-memory MCP server is running:" -ForegroundColor Yellow
        Write-Host "  mcporter list" -ForegroundColor Yellow
        Write-Host "  mcporter list neural-memory --schema" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To resume from where this stopped, run:" -ForegroundColor Yellow
        Write-Host "  .\ingest_triples.ps1 -VaultPath '$VaultPath' -StartAt $i" -ForegroundColor Yellow
        break
    }

    Start-Sleep -Milliseconds $DelayMs
}

# ── SUMMARY ───────────────────────────────────────────────────────────────────
$elapsed  = (Get-Date) - $runStart
$duration = "$([Math]::Floor($elapsed.TotalMinutes))m $($elapsed.Seconds)s"

Write-Host ""
Write-Host "=== INGEST COMPLETE ===" -ForegroundColor Cyan
Write-Host "  Successful: $success" -ForegroundColor Green
Write-Host "  Failed:     $fail"    -ForegroundColor $(if ($fail -gt 0) { 'Red' } else { 'Gray' })
Write-Host "  Skipped:    $skip"    -ForegroundColor Gray
Write-Host "  Duration:   $duration" -ForegroundColor White
Write-Host "  Log:        $LogPath" -ForegroundColor Gray
Write-Host ""

if ($success -gt 0 -and -not $DryRun) {
    Write-Host "Your neural graph has been seeded with $success facts from your history." -ForegroundColor Green
    Write-Host "Session 000 complete. Your AI already knows you." -ForegroundColor Cyan
}

if ($fail -gt 0) {
    Write-Host ""
    Write-Host "Some facts failed to ingest. Check $LogPath for details." -ForegroundColor Yellow
    Write-Host "You can retry failed items by checking the log for fact numbers" -ForegroundColor Yellow
    Write-Host "and rerunning with -StartAt <number>." -ForegroundColor Yellow
}

# Write summary to log
$summary = @"
=== Run Complete: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===
Success: $success | Failed: $fail | Skipped: $skip | Duration: $duration
"@
Add-Content -Path $LogPath -Value $summary -Encoding UTF8
