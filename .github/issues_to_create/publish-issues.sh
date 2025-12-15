#!/bin/bash
# Publish all priority issues to GitHub

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
ISSUES_DIR="${REPO_ROOT}/.github/issues_to_create"

echo "🚀 Publishing REPLAYER priority issues to GitHub..."
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: gh CLI not installed"
    echo "Install: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

# Function to extract frontmatter field
extract_field() {
    local file="$1"
    local field="$2"
    grep "^${field}:" "$file" | cut -d'"' -f2 | head -1
}

# Function to extract body (remove frontmatter)
extract_body() {
    local file="$1"
    sed '1,/^---$/d; /^---$/d' "$file"
}

# Function to extract labels
extract_labels() {
    local file="$1"
    grep "^labels:" "$file" | cut -d: -f2 | tr -d ' '
}

# Publish issues in order
ISSUES=(
    "priority-02-server-state-authority.md"
    "priority-03-live-game-recording.md"
    "priority-04-rag-knowledge-base.md"
    "priority-05-rl-model-integration.md"
    "priority-06-browser-live-trading.md"
    "priority-07-portfolio-dashboard.md"
    "priority-08-player-profile-ui.md"
)

for issue_file in "${ISSUES[@]}"; do
    issue_path="${ISSUES_DIR}/${issue_file}"

    if [[ ! -f "$issue_path" ]]; then
        echo "⚠️  Warning: $issue_file not found, skipping..."
        continue
    fi

    echo "📝 Publishing: $issue_file"

    # Extract metadata
    title=$(extract_field "$issue_path" "title")
    labels=$(extract_labels "$issue_path")
    body=$(extract_body "$issue_path")

    # Create issue
    issue_url=$(echo "$body" | gh issue create \
        --title "$title" \
        --body-file - \
        --label "$labels" 2>&1 | grep -oP 'https://\S+' || echo "")

    if [[ -n "$issue_url" ]]; then
        echo "✅ Created: $issue_url"
    else
        echo "❌ Failed to create issue for $issue_file"
    fi

    echo ""

    # Rate limit: wait 1 second between issues
    sleep 1
done

echo "🎉 All issues published!"
echo ""
echo "View issues: gh issue list"
echo "Or visit: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/issues"
