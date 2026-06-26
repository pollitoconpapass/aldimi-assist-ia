#!/bin/bash

# Exportar las variables de entorno desde el .env
load_env() {
    local env_file="${1:-.env}"
    
    if [ ! -f "$env_file" ]; then
        echo "Error: $env_file not found!" >&2
        return 1
    fi

    echo "Loading environment variables from $env_file..."
    
    while IFS= read -r line; do
        # Skip != VAR=VALUE
        if [[ "$line" =~ ^[[:alnum:]_]+= ]]; then
            export "$line"
        fi
    done < <(grep -v '^\s*#' "$env_file" | grep -v '^\s*$')
    
    echo "Environment variables loaded successfully!"
    return 0
}


if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    echo "Error: This script must be sourced, not executed:" >&2
    echo "  source $0" >&2
    echo "  . $0" >&2
    exit 1
fi

load_env "${1:-.env}"

echo -e "\nLoaded environment variables:"
grep -v '^\s*#' "${1:-.env}" | grep -v '^\s*$' | cut -d'=' -f1 | sed 's/^/  /'