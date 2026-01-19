#!/bin/sh
# wait-for-it.sh: Wait for a service to be available

set -e

host="$1"
shift
cmd="$@"

until nc -z $(echo $host | cut -d: -f1) $(echo $host | cut -d: -f2); do
  >&2 echo "Waiting for $host to be ready..."
  sleep 2
done

>&2 echo "$host is ready - executing command"
exec $cmd
