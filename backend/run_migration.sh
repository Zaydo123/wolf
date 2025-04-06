#!/bin/bash

# Check if the PostgreSQL password is provided
if [ -z "$1" ]; then
  echo "Usage: ./run_migration.sh <postgres_password>"
  exit 1
fi

# Set PostgreSQL password
export PGPASSWORD="$1"

# Run the migration
echo "Running portfolio price columns migration..."
psql -U postgres -h localhost -d postgres -f migrations/20240510_add_portfolio_current_price.sql

# Clear the password from environment
unset PGPASSWORD

echo "Migration completed." 