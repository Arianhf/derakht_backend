#!/bin/bash

# Derakht Backend Test Runner
# Quick script to run tests with common options

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print banner
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   Derakht Backend Test Runner${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Function to display usage
usage() {
    echo "Usage: ./run_tests.sh [option]"
    echo ""
    echo "Options:"
    echo "  all          Run all tests (default)"
    echo "  unit         Run only unit tests"
    echo "  integration  Run only integration tests"
    echo "  e2e          Run only end-to-end tests"
    echo "  payment      Run payment-related tests"
    echo "  auth         Run authentication tests"
    echo "  cart         Run cart tests"
    echo "  coverage     Run tests with HTML coverage report"
    echo "  fast         Run tests in parallel (faster)"
    echo "  failed       Run only failed tests from last run"
    echo "  shop         Run shop app tests only"
    echo "  users        Run users app tests only"
    echo "  stories      Run stories app tests only"
    echo "  ci           Run tests as in CI/CD"
    echo "  help         Show this help message"
    echo ""
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Please run: pip install -r requirements-test.txt"
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready -q 2>/dev/null; then
    echo -e "${YELLOW}Warning: PostgreSQL may not be running${NC}"
    echo "Tests require a running PostgreSQL instance"
    echo ""
fi

# Parse command line argument
COMMAND=${1:-all}

case $COMMAND in
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        pytest -v
        ;;
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        pytest -v -m unit
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        pytest -v -m integration
        ;;
    e2e)
        echo -e "${GREEN}Running end-to-end tests...${NC}"
        pytest -v -m e2e
        ;;
    payment)
        echo -e "${GREEN}Running payment tests...${NC}"
        pytest -v -m payment
        ;;
    auth)
        echo -e "${GREEN}Running authentication tests...${NC}"
        pytest -v -m auth
        ;;
    cart)
        echo -e "${GREEN}Running cart tests...${NC}"
        pytest -v -m cart
        ;;
    coverage)
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        pytest --cov=. --cov-report=html --cov-report=term-missing -v
        echo ""
        echo -e "${GREEN}Coverage report generated!${NC}"
        echo "Open htmlcov/index.html to view the report"
        ;;
    fast)
        echo -e "${GREEN}Running tests in parallel...${NC}"
        pytest -n auto -v
        ;;
    failed)
        echo -e "${GREEN}Running only failed tests from last run...${NC}"
        pytest --lf -v
        ;;
    shop)
        echo -e "${GREEN}Running shop app tests...${NC}"
        pytest shop/tests/ -v
        ;;
    users)
        echo -e "${GREEN}Running users app tests...${NC}"
        pytest users/tests/ -v
        ;;
    stories)
        echo -e "${GREEN}Running stories app tests...${NC}"
        pytest stories/tests/ -v
        ;;
    ci)
        echo -e "${GREEN}Running tests as in CI/CD...${NC}"
        export DJANGO_SETTINGS_MODULE=derakht.settings_test
        pytest --cov=. \
               --cov-report=xml \
               --cov-report=html \
               --cov-report=term-missing \
               --cov-fail-under=80 \
               --maxfail=5 \
               -v
        ;;
    help)
        usage
        exit 0
        ;;
    *)
        echo -e "${RED}Error: Unknown option '$COMMAND'${NC}"
        echo ""
        usage
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Tests completed successfully!${NC}"
else
    echo ""
    echo -e "${RED}❌ Tests failed!${NC}"
    exit 1
fi
