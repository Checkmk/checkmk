#!/bin/bash

# Default values
PORT="1521"
VERSION=""

# Function to show usage
usage() {
    echo "Usage: $0 -v <version> [-P <port>]"
    echo "  -v, --version   Oracle version (23, 11, 12, 19)"
    echo "  -P, --port      Database port (default: 1521)"
    exit 1
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -v | --version)
            VERSION="$2"
            shift
            ;;
        -P | --port)
            PORT="$2"
            shift
            ;;
        *)
            echo "Unknown parameter passed: $1"
            usage
            ;;
    esac
    shift
done

if [ -z "$VERSION" ]; then
    echo "Error: Version is required."
    usage
fi

# Map version to service name
case $VERSION in
    23) SERVICE="oracle-free" ;;
    11) SERVICE="oracle-xe" ;;
    12 | 12c) SERVICE="oracle-12c" ;;
    19 | 19c) SERVICE="oracle-19c" ;;
    *)
        echo "Error: Unsupported version '$VERSION'. Supported versions: 23, 11, 12, 19"
        exit 1
        ;;
esac

# Export environment variables for docker-compose
export ORACLE_PASSWORD="oracle"
export ORACLE_PORT="$PORT"

echo "Starting Oracle $VERSION ($SERVICE) on port $PORT with password 'oracle'..."

# Run docker compose
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d "$SERVICE"

# Wait for healthcheck for supported versions
if [[ "$VERSION" == "23" || "$VERSION" == "11" || "$VERSION" == "12" || "$VERSION" == "12c" || "$VERSION" == "19" || "$VERSION" == "19c" ]]; then
    echo "Waiting for $SERVICE to be healthy..."

    while true; do
        CONTAINER_ID=$(docker compose -f "$SCRIPT_DIR/docker-compose.yml" ps -q "$SERVICE")
        STATUS=$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_ID")

        if [ "$STATUS" == "healthy" ]; then
            echo "$SERVICE is ready!"
            break
        fi

        if [ "$STATUS" == "unhealthy" ]; then
            echo "Error: $SERVICE failed to start (unhealthy)."
            exit 1
        fi

        echo "Current status: $STATUS. Waiting..."
        sleep 10
    done

    # Determine SID based on version
    if [ "$VERSION" == "23" ]; then
        SID="FREE"
        SERVICE_NAME="FREE"
    elif [ "$VERSION" == "11" ]; then
        SID="XE"
        SERVICE_NAME="XE"
    elif [[ "$VERSION" == "12" || "$VERSION" == "12c" ]]; then
        SID="XE"
        SERVICE_NAME="xe.oracle.docker"
    elif [[ "$VERSION" == "19" || "$VERSION" == "19c" ]]; then
        SID="ORCLCDB"
        SERVICE_NAME="ORCLCDB"
    fi

    echo ""
    echo "=================================================="
    echo "             Database Ready to Use                "
    echo "=================================================="
    echo "Host:      localhost"
    echo "Port:      $PORT"
    echo "SID:       $SID"
    echo "Service:   $SERVICE_NAME"
    echo "Password:  oracle"
    echo "=================================================="
fi
