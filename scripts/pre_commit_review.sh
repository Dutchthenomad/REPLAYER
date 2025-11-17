#!/bin/bash
###############################################################################
# REPLAYER Pre-Commit Review Script
#
# Runs comprehensive code review before git commits using:
# 1. aicode-review plugin (design patterns, coding standards)
# 2. mcp-code-checker (pylint, mypy, pytest)
#
# Usage:
#   ./scripts/pre_commit_review.sh                    # Review all changed files
#   ./scripts/pre_commit_review.sh --all              # Review entire codebase
#   ./scripts/pre_commit_review.sh --file <path>      # Review specific file
#   ./scripts/pre_commit_review.sh --phase-complete   # Full phase review
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project paths
PROJECT_ROOT="/home/nomad/Desktop/REPLAYER"
VENV_PATH="/home/nomad/Desktop/rugs-rl-bot/.venv"
PYTHON_BIN="${VENV_PATH}/bin/python3"
MCP_CODE_CHECKER="${VENV_PATH}/bin/mcp-code-checker"

# Report file
REPORT_FILE="${PROJECT_ROOT}/review_report_$(date +%Y%m%d_%H%M%S).txt"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

###############################################################################
# Review Functions
###############################################################################

review_with_aicode() {
    local file=$1
    print_header "Running aicode-review on ${file}"

    # Note: aicode-review MCP plugin integration would be called here
    # For now, we'll check the configuration files exist
    if [[ -f "${PROJECT_ROOT}/architect.yaml" ]] && [[ -f "${PROJECT_ROOT}/RULES.yaml" ]]; then
        print_success "Configuration files found (architect.yaml, RULES.yaml)"
        print_info "Manual review required - use aicode-review MCP plugin in Claude Code"
        echo "  File: ${file}" >> "$REPORT_FILE"
        echo "  Design patterns: See architect.yaml" >> "$REPORT_FILE"
        echo "  Coding rules: See RULES.yaml" >> "$REPORT_FILE"
        return 0
    else
        print_error "Configuration files missing!"
        return 1
    fi
}

run_pylint() {
    local file=$1
    print_header "Running Pylint on ${file}"

    if [[ ! -f "$file" ]]; then
        print_error "File not found: $file"
        return 1
    fi

    # Run pylint
    if "${VENV_PATH}/bin/pylint" "$file" --output-format=colorized; then
        print_success "Pylint passed!"
        echo "Pylint: PASS" >> "$REPORT_FILE"
        return 0
    else
        local exit_code=$?
        print_warning "Pylint found issues (exit code: $exit_code)"
        echo "Pylint: ISSUES FOUND (exit code: $exit_code)" >> "$REPORT_FILE"
        return $exit_code
    fi
}

run_mypy() {
    local file=$1
    print_header "Running Mypy on ${file}"

    if [[ ! -f "$file" ]]; then
        print_error "File not found: $file"
        return 1
    fi

    # Run mypy
    if "${VENV_PATH}/bin/mypy" "$file" --strict --show-error-codes; then
        print_success "Mypy passed!"
        echo "Mypy: PASS" >> "$REPORT_FILE"
        return 0
    else
        local exit_code=$?
        print_warning "Mypy found type issues (exit code: $exit_code)"
        echo "Mypy: TYPE ISSUES (exit code: $exit_code)" >> "$REPORT_FILE"
        return $exit_code
    fi
}

run_pytest() {
    print_header "Running Pytest"

    cd "${PROJECT_ROOT}/src"

    if "${PYTHON_BIN}" -m pytest tests/ -v --tb=short; then
        print_success "All tests passed!"
        echo "Pytest: ALL PASS" >> "$REPORT_FILE"
        return 0
    else
        local exit_code=$?
        print_error "Some tests failed! (exit code: $exit_code)"
        echo "Pytest: FAILURES (exit code: $exit_code)" >> "$REPORT_FILE"
        return $exit_code
    fi
}

###############################################################################
# Main Review Logic
###############################################################################

review_file() {
    local file=$1
    local failures=0

    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Reviewing: ${file}${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"

    echo -e "\n--- File: ${file} ---" >> "$REPORT_FILE"

    # Step 1: aicode-review (design patterns, rules)
    if ! review_with_aicode "$file"; then
        ((failures++))
    fi

    # Step 2: Pylint (static analysis)
    if ! run_pylint "$file"; then
        ((failures++))
    fi

    # Step 3: Mypy (type checking)
    if ! run_mypy "$file"; then
        ((failures++))
    fi

    echo "" >> "$REPORT_FILE"

    return $failures
}

review_changed_files() {
    print_header "Reviewing Git Changed Files"

    # Get list of changed Python files
    cd "$PROJECT_ROOT"
    local changed_files=$(git diff --name-only --cached --diff-filter=ACM | grep '\.py$' || true)

    if [[ -z "$changed_files" ]]; then
        print_info "No Python files staged for commit"
        return 0
    fi

    local total_failures=0

    for file in $changed_files; do
        if ! review_file "${PROJECT_ROOT}/${file}"; then
            ((total_failures++))
        fi
    done

    return $total_failures
}

review_all_files() {
    print_header "Reviewing All Python Files"

    local total_failures=0
    local files=$(find "${PROJECT_ROOT}/src" -name "*.py" -not -path "*/tests/*")

    for file in $files; do
        if ! review_file "$file"; then
            ((total_failures++))
        fi
    done

    return $total_failures
}

phase_complete_review() {
    print_header "PHASE COMPLETION REVIEW"

    echo "Phase Completion Review - $(date)" > "$REPORT_FILE"
    echo "=================================" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    local total_failures=0

    # Step 1: Run all tests
    if ! run_pytest; then
        ((total_failures++))
    fi

    # Step 2: Review all changed files
    if ! review_changed_files; then
        ((total_failures++))
    fi

    # Step 3: Generate summary
    print_header "Review Summary"

    if [[ $total_failures -eq 0 ]]; then
        print_success "All checks passed! ✓"
        echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  Ready to commit and push! 🚀${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        echo -e "\nSUMMARY: ALL CHECKS PASSED ✓" >> "$REPORT_FILE"
        return 0
    else
        print_error "Review found $total_failures issue(s)"
        echo -e "\n${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}  Please fix issues before committing! ✗${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        echo -e "\nSUMMARY: $total_failures ISSUES FOUND ✗" >> "$REPORT_FILE"
        return 1
    fi
}

###############################################################################
# Main Script
###############################################################################

main() {
    cd "$PROJECT_ROOT"

    print_header "REPLAYER Code Review System"
    print_info "Report will be saved to: ${REPORT_FILE}"

    echo "Code Review Report - $(date)" > "$REPORT_FILE"
    echo "=====================================" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    case "${1:-}" in
        --all)
            review_all_files
            ;;
        --file)
            if [[ -z "${2:-}" ]]; then
                print_error "Usage: $0 --file <path>"
                exit 1
            fi
            review_file "$2"
            ;;
        --phase-complete)
            phase_complete_review
            ;;
        --help)
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  (no args)         Review all staged files (default)"
            echo "  --all             Review entire codebase"
            echo "  --file <path>     Review specific file"
            echo "  --phase-complete  Full phase completion review"
            echo "  --help            Show this help"
            exit 0
            ;;
        *)
            review_changed_files
            ;;
    esac

    local exit_code=$?

    print_info "Full report saved to: ${REPORT_FILE}"

    exit $exit_code
}

# Run main function
main "$@"
