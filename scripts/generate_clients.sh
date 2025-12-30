#!/usr/bin/env bash
# Generate client SDKs from LMSilo OpenAPI specs
#
# Prerequisites:
#   npm install -g @openapitools/openapi-generator-cli
#   OR
#   brew install openapi-generator
#
# Usage:
#   ./scripts/generate_clients.sh [service]
#   ./scripts/generate_clients.sh          # Generate all clients
#   ./scripts/generate_clients.sh locate   # Generate only locate client

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLIENTS_DIR="$PROJECT_ROOT/clients"

# Service configurations
declare -A SERVICES=(
    ["locate"]="http://localhost:8081"
    ["transcribe"]="http://localhost:8082"
    ["translate"]="http://localhost:8083"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if openapi-generator is available
check_generator() {
    if command -v openapi-generator &> /dev/null; then
        GENERATOR_CMD="openapi-generator"
    elif command -v openapi-generator-cli &> /dev/null; then
        GENERATOR_CMD="openapi-generator-cli"
    elif command -v npx &> /dev/null; then
        GENERATOR_CMD="npx @openapitools/openapi-generator-cli"
    else
        log_error "openapi-generator not found. Install with:"
        echo "  npm install -g @openapitools/openapi-generator-cli"
        echo "  OR"
        echo "  brew install openapi-generator"
        exit 1
    fi
    log_info "Using generator: $GENERATOR_CMD"
}

# Fetch OpenAPI spec from service
fetch_spec() {
    local service=$1
    local url="${SERVICES[$service]}"
    local spec_file="$CLIENTS_DIR/specs/${service}_openapi.json"
    
    mkdir -p "$CLIENTS_DIR/specs"
    
    log_info "Fetching OpenAPI spec from $url/openapi.json"
    
    if ! curl -sf "$url/openapi.json" -o "$spec_file" 2>/dev/null; then
        log_warn "Could not fetch spec from running service, trying static file..."
        
        # Try static file as fallback
        local static_spec="$PROJECT_ROOT/$service/openapi.json"
        if [ -f "$static_spec" ]; then
            cp "$static_spec" "$spec_file"
            log_info "Using static spec file"
        else
            log_error "No OpenAPI spec available for $service"
            return 1
        fi
    fi
    
    echo "$spec_file"
}

# Generate TypeScript client
generate_typescript() {
    local service=$1
    local spec_file=$2
    local output_dir="$CLIENTS_DIR/typescript/$service"
    
    log_info "Generating TypeScript client for $service..."
    
    $GENERATOR_CMD generate \
        -i "$spec_file" \
        -g typescript-fetch \
        -o "$output_dir" \
        --additional-properties=npmName=@lmsilo/${service}-client \
        --additional-properties=npmVersion=1.0.0 \
        --additional-properties=supportsES6=true \
        --additional-properties=typescriptThreePlus=true \
        --additional-properties=withInterfaces=true \
        --skip-validate-spec
    
    # Add package.json if not exists
    if [ ! -f "$output_dir/package.json" ]; then
        cat > "$output_dir/package.json" << EOF
{
  "name": "@lmsilo/${service}-client",
  "version": "1.0.0",
  "description": "TypeScript client for LMSilo $service service",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "prepublishOnly": "npm run build"
  },
  "dependencies": {},
  "devDependencies": {
    "typescript": "^5.4.0"
  }
}
EOF
    fi
    
    log_info "TypeScript client generated at $output_dir"
}

# Generate Python client
generate_python() {
    local service=$1
    local spec_file=$2
    local output_dir="$CLIENTS_DIR/python/$service"
    
    log_info "Generating Python client for $service..."
    
    $GENERATOR_CMD generate \
        -i "$spec_file" \
        -g python \
        -o "$output_dir" \
        --additional-properties=packageName=lmsilo_${service} \
        --additional-properties=projectName=lmsilo-${service}-client \
        --additional-properties=packageVersion=1.0.0 \
        --skip-validate-spec
    
    log_info "Python client generated at $output_dir"
}

# Generate clients for a service
generate_service() {
    local service=$1
    
    log_info "Processing service: $service"
    
    local spec_file
    if ! spec_file=$(fetch_spec "$service"); then
        log_error "Skipping $service due to missing spec"
        return 1
    fi
    
    generate_typescript "$service" "$spec_file"
    generate_python "$service" "$spec_file"
    
    log_info "Completed $service client generation"
}

# Main
main() {
    check_generator
    
    local services_to_generate=()
    
    if [ $# -eq 0 ]; then
        # Generate all
        services_to_generate=("${!SERVICES[@]}")
    else
        # Generate specific service
        for svc in "$@"; do
            if [[ -v "SERVICES[$svc]" ]]; then
                services_to_generate+=("$svc")
            else
                log_error "Unknown service: $svc"
                log_info "Available services: ${!SERVICES[*]}"
                exit 1
            fi
        done
    fi
    
    log_info "Generating clients for: ${services_to_generate[*]}"
    
    for service in "${services_to_generate[@]}"; do
        generate_service "$service" || true
    done
    
    log_info "Client generation complete!"
    echo ""
    echo "Generated clients are in:"
    echo "  TypeScript: $CLIENTS_DIR/typescript/"
    echo "  Python:     $CLIENTS_DIR/python/"
}

main "$@"
