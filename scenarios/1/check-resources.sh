#!/bin/bash

# GCP Resources Verification Script
# Usage: ./check-resources.sh [task-1|task-2|task-3|all]

# Set default region if not provided
REGION=${REGION:-europe-central2}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    elif [ "$status" = "INFO" ]; then
        echo -e "${BLUE}ℹ${NC} $message"
        # INFO messages don't count toward pass/fail totals
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        # WARN messages don't count toward pass/fail totals
    fi
}

# Function to check if service account exists
check_service_account() {
    local sa_name=$1
    local project_id=$(gcloud config get-value project 2>/dev/null)
    
    if gcloud iam service-accounts describe "${sa_name}@${project_id}.iam.gserviceaccount.com" &>/dev/null; then
        print_status "PASS" "Service Account: $sa_name"
        return 0
    else
        print_status "FAIL" "Service Account: $sa_name (not found)"
        return 1
    fi
}

# Function to check if VPC exists
check_vpc() {
    local vpc_name=$1
    
    if gcloud compute networks describe "$vpc_name" &>/dev/null; then
        print_status "PASS" "VPC Network: $vpc_name"
        return 0
    else
        print_status "FAIL" "VPC Network: $vpc_name (not found)"
        return 1
    fi
}

# Function to check if subnet exists
check_subnet() {
    local subnet_name=$1
    local region=$2
    
    if gcloud compute networks subnets describe "$subnet_name" --region="$region" &>/dev/null; then
        print_status "PASS" "Subnet: $subnet_name (region: $region)"
        return 0
    else
        print_status "FAIL" "Subnet: $subnet_name in region $region (not found)"
        return 1
    fi
}

# Function to check if Pub/Sub topic exists
check_pubsub_topic() {
    local topic_name=$1
    
    if gcloud pubsub topics describe "$topic_name" &>/dev/null; then
        print_status "PASS" "Pub/Sub Topic: $topic_name"
        return 0
    else
        print_status "FAIL" "Pub/Sub Topic: $topic_name (not found)"
        return 1
    fi
}

# Function to check if Cloud SQL instance exists
check_sql_instance() {
    local instance_name=$1
    
    if gcloud sql instances describe "$instance_name" &>/dev/null; then
        print_status "PASS" "Cloud SQL Instance: $instance_name"
        return 0
    else
        print_status "FAIL" "Cloud SQL Instance: $instance_name (not found)"
        return 1
    fi
}

# Function to check if Cloud SQL database exists
check_sql_database() {
    local instance_name=$1
    local database_name=$2
    
    if gcloud sql databases describe "$database_name" --instance="$instance_name" &>/dev/null; then
        print_status "PASS" "Cloud SQL Database: $database_name (instance: $instance_name)"
        return 0
    else
        print_status "FAIL" "Cloud SQL Database: $database_name (not found in instance: $instance_name)"
        return 1
    fi
}

# Function to check if Cloud SQL user exists
check_sql_user() {
    local instance_name=$1
    local user_name=$2
    
    if gcloud sql users list --instance="$instance_name" --format="value(name)" | grep -q "$user_name"; then
        print_status "PASS" "Cloud SQL User: $user_name (instance: $instance_name)"
        return 0
    else
        print_status "FAIL" "Cloud SQL User: $user_name (not found in instance: $instance_name)"
        return 1
    fi
}

# Function to check if VPC peering exists
check_vpc_peering() {
    local network_name=$1
    local peering_name="servicenetworking-googleapis-com"
    
    # Check if the reserved IP range exists
    if gcloud compute addresses describe "google-managed-services-$network_name" --global &>/dev/null; then
        print_status "PASS" "VPC Peering IP Range: google-managed-services-$network_name"
    else
        print_status "FAIL" "VPC Peering IP Range: google-managed-services-$network_name (not found)"
    fi

    # Check if the peering connection exists
    # Using network describe is more reliable than peerings list for checking existence
    if gcloud compute networks describe "$network_name" --format="value(peerings.name)" 2>/dev/null | grep -q "$peering_name"; then
        print_status "PASS" "VPC Peering Connection: $peering_name"
        return 0
    else
        print_status "FAIL" "VPC Peering Connection: $peering_name (not found in network: $network_name)"
        return 1
    fi
}

# Function to check if VPC connector exists
check_vpc_connector() {
    local connector_name=$1
    local region=${2:-$REGION}
    
    if gcloud compute networks vpc-access connectors describe "$connector_name" --region="$region" &>/dev/null; then
        print_status "PASS" "VPC Connector: $connector_name"
        return 0
    else
        print_status "FAIL" "VPC Connector: $connector_name (not found in region: $region)"
        return 1
    fi
}

# Function to check if Cloud Run service exists
check_cloud_run_service() {
    local service_name=$1
    local region=${2:-$REGION}
    
    if gcloud run services describe "$service_name" --region="$region" &>/dev/null; then
        print_status "PASS" "Cloud Run Service: $service_name"
        return 0
    else
        print_status "FAIL" "Cloud Run Service: $service_name (not found in region: $region)"
        return 1
    fi
}

# Function to check if Cloud Function exists
check_cloud_function() {
    local function_name=$1
    local region=${2:-$REGION}
    
    if gcloud functions describe "$function_name" --region="$region" &>/dev/null; then
        print_status "PASS" "Cloud Function: $function_name"
        return 0
    else
        print_status "FAIL" "Cloud Function: $function_name (not found in region: $region)"
        return 1
    fi
}

# Function to check if IAM role is assigned
check_iam_role() {
    local sa_name=$1
    local role=$2
    local project_id=$(gcloud config get-value project 2>/dev/null)
    local sa_email="serviceAccount:${sa_name}@${project_id}.iam.gserviceaccount.com"
    
    # Check if the role is bound to the service account
    if gcloud projects get-iam-policy "$project_id" \
        --flatten="bindings[].members" \
        --filter="bindings.members:${sa_email} AND bindings.role:${role}" \
        --format="value(bindings.role)" 2>/dev/null | grep -q "$role"; then
        print_status "PASS" "IAM Role: $role assigned to $sa_name"
        return 0
    else
        print_status "FAIL" "IAM Role: $role not assigned to $sa_name"
        return 1
    fi
}

# Function to run Task 1 checks
check_task1() {
    echo -e "\n${BLUE}=== Task 1: Independent Resources ===${NC}"
    
    # Service Accounts
    echo -e "\n${YELLOW}Service Accounts:${NC}"
    check_service_account "hello-frontend-sa"
    check_service_account "hello-backend-sa"
    check_service_account "hello-function-sa"
    
    # VPC and Subnet
    echo -e "\n${YELLOW}Network Resources:${NC}"
    check_vpc "hello-game-vpc"
    check_subnet "hello-game-subnet" "$REGION"
    
    # Pub/Sub Topic
    echo -e "\n${YELLOW}Messaging:${NC}"
    check_pubsub_topic "hello-game-submissions"
}

# Function to run Task 2 checks (placeholder)
check_task2() {
    echo -e "\n${BLUE}=== Task 2: Application Deployment ===${NC}"

    # VPC Peering
    echo -e "\n${YELLOW}VPC Peering:${NC}"
    check_vpc_peering "hello-game-vpc"
    
    # Cloud SQL Instance
    echo -e "\n${YELLOW}Cloud SQL:${NC}"
    check_sql_instance "hello-game-db"
    check_sql_database "hello-game-db" "hello-game-submissions-db"
    check_sql_user "hello-game-db" "hello-backend-sa@$PROJECT_ID.iam"
    check_sql_user "hello-game-db" "hello-function-sa@$PROJECT_ID.iam"

    # Print a warning that we can't really check for DB users permissions inside the DB
    print_status "WARN" "Cannot verify Cloud SQL user permissions via gcloud CLI"
    print_status "WARN" "I am just a simple script and cannot do it for you :("
}

# Function to run Task 3 checks
check_task3() {
    echo -e "\n${BLUE}=== Task 3: Backend Deployment ===${NC}"

    # Private Google Access
    echo -e "\n${YELLOW}Private Google Access:${NC}"
    local subnet_name="hello-game-subnet"
    if gcloud compute networks subnets describe "$subnet_name" --region="$REGION" --format="value(privateIpGoogleAccess)" 2>/dev/null | grep -q "True"; then
        print_status "PASS" "Private Google Access enabled on $subnet_name"
    else
        print_status "FAIL" "Private Google Access NOT enabled on $subnet_name"
    fi
    
    # Cloud Run Backend
    echo -e "\n${YELLOW}Cloud Run Backend:${NC}"
    check_cloud_run_service "hello-backend"

    # IAM Roles
    echo -e "\n${YELLOW}IAM Roles:${NC}"
    check_iam_role "hello-backend-sa" "roles/cloudsql.instanceUser"
    check_iam_role "hello-backend-sa" "roles/cloudsql.client"
}

# Task 4 Verification
check_task4() {
    echo -e "\n${BLUE}=== Verifying Task 4 Resources ===${NC}"

    # Cloud Run Frontend
    echo -e "\n${YELLOW}Cloud Run Frontend:${NC}"
    check_cloud_run_service "hello-frontend"

    # IAM Roles
    echo -e "\n${YELLOW}IAM Roles:${NC}"
    # Check if frontend SA has run.invoker on backend service
    # Note: This is a bit tricky to check via simple gcloud command without parsing JSON policy
    # So we'll check project-level or resource-level binding existence in a simplified way
    
    local project_id=$(gcloud config get-value project 2>/dev/null)
    
    # Check run.invoker on backend service
    if gcloud run services get-iam-policy hello-backend --region="$REGION" --format=json 2>/dev/null | grep -q "hello-frontend-sa@${project_id}.iam.gserviceaccount.com"; then
         print_status "PASS" "IAM Binding: hello-frontend-sa has access to hello-backend"
    else
         print_status "FAIL" "IAM Binding: hello-frontend-sa missing access to hello-backend"
    fi

    # Check pubsub.publisher on topic
    if gcloud pubsub topics get-iam-policy hello-game-submissions --format=json 2>/dev/null | grep -q "hello-frontend-sa@${project_id}.iam.gserviceaccount.com"; then
         print_status "PASS" "IAM Binding: hello-frontend-sa has publisher access to hello-game-submissions"
    else
         print_status "FAIL" "IAM Binding: hello-frontend-sa missing publisher access to hello-game-submissions"
    fi
}

# Task 5 Verification
check_task5() {
    echo -e "\n${BLUE}=== Verifying Task 5 Resources ===${NC}"
    
    # Cloud Function
    echo -e "\n${YELLOW}Cloud Function:${NC}"
    check_cloud_function "hello-function"

    # IAM Roles
    echo -e "\n${YELLOW}IAM Roles:${NC}"
    check_iam_role "hello-function-sa" "roles/cloudsql.instanceUser"
    check_iam_role "hello-function-sa" "roles/cloudsql.client"

    local project_id=$(gcloud config get-value project 2>/dev/null)

    # Check run.invoker on function service
    # Note: Cloud Functions (2nd gen) are deployed as Cloud Run services
    if gcloud run services get-iam-policy hello-function --region="$REGION" --format=json 2>/dev/null | grep -q "hello-function-sa@${project_id}.iam.gserviceaccount.com"; then
         print_status "PASS" "IAM Binding: hello-function-sa has access to hello-function (self-invocation)"
    else
         print_status "FAIL" "IAM Binding: hello-function-sa missing access to hello-function"
    fi
}

# Function to display usage
show_usage() {
    echo "Usage: $0 [task-1|task-2|task-3|task-4|task-5|all]"
    echo ""
    echo "Arguments:"
    echo "  task-1    Verify Task 1 resources (Service Accounts, VPC, Subnet, Pub/Sub)"
    echo "  task-2    Verify Task 2 resources (Cloud SQL, DB Users)"
    echo "  task-3    Verify Task 3 resources (Cloud Run Backend, VPC Connector)"
    echo "  task-4    Verify Task 4 resources (Cloud Run Frontend, IAM Roles)"
    echo "  task-5    Verify Task 5 resources (Cloud Function, IAM Roles)"
    echo "  all       Run all task verifications"
    echo ""
    echo "Environment Variables:"
    echo "  REGION    GCP region to use (default: europe-central2)"
    echo ""
    echo "Examples:"
    echo "  $0 task-1"
    echo "  REGION=us-central1 $0 task-1"
    echo "  $0 all"
}

# Function to print summary
print_summary() {
    echo -e "\n${BLUE}=== Summary ===${NC}"
    if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
        echo -e "${GREEN}All checks passed!${NC} ($PASSED_CHECKS/$TOTAL_CHECKS)"
        exit 0
    else
        local failed_checks=$((TOTAL_CHECKS - PASSED_CHECKS))
        echo -e "${RED}Some checks failed.${NC} Passed: $PASSED_CHECKS, Failed: $failed_checks, Total: $TOTAL_CHECKS"
        exit 1
    fi
}

# Main script logic
main() {
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_status "FAIL" "gcloud CLI is not installed or not in PATH"
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_status "FAIL" "Not authenticated with gcloud. Run 'gcloud auth login'"
        exit 1
    fi
    
    # Get current project
    local project_id=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$project_id" ]; then
        print_status "FAIL" "No project set. Run 'gcloud config set project PROJECT_ID'"
        exit 1
    fi
    
    print_status "INFO" "Current project: $project_id"
    print_status "INFO" "Using region: $REGION"
    
    # Process arguments
    case "${1:-help}" in
        "task-1")
            check_task1
            ;;
        "task-2")
            check_task2
            ;;
        "task-3")
            check_task3
            ;;
        "task-4")
            check_task4
            ;;
        "task-5")
            check_task5
            ;;
        "all")
            check_task1
            check_task2
            check_task3
            check_task4
            check_task5
            ;;
        "help"|"-h"|"--help"|*)
            show_usage
            exit 0
            ;;
    esac
    
    print_summary
}

# Run main function with all arguments
main "$@"
