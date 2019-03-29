#!/bin/bash

# # Bash strict mode
# set -euo pipefail

# # ============================
# # jverner POCITADLO
# /expSW/SOFTWARE/bin/pocitadlo
# # ============================

## FIND DIRECTORY OF THE SCRIPT
## ============================
SOURCE="${BASH_SOURCE[0]}"
# resolve $SOURCE until the file is no longer a symlink
while [ -h "$SOURCE" ]; do
  SCRIPTDIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
  [[ $SOURCE != /* ]] && SOURCE="$SCRIPTDIR/$SOURCE"
done
SCRIPTDIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null && pwd )"

## ACTIVATE VIRTUAL ENVIRONMENT AND RUN APP
## ========================================
source "$SCRIPTDIR"/.venv/bin/activate
#export LD_LIBRARY_PATH="$SCRIPTDIR"/LD_LIB
python "$SCRIPTDIR"/kbl2nas.py "$@"


## MORE VERBOSE VARIANT OF THE ABOVE
## =================================
# SOURCE="${BASH_SOURCE[0]}"
# while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
#   TARGET="$(readlink "$SOURCE")"
#   if [[ $TARGET == /* ]]; then
#     echo "SOURCE '$SOURCE' is an absolute symlink to '$TARGET'"
#     SOURCE="$TARGET"
#   else
#     DIR="$( dirname "$SOURCE" )"
#     echo "SOURCE '$SOURCE' is a relative symlink to '$TARGET' (relative to '$DIR')"
#     SOURCE="$DIR/$TARGET" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
#   fi
# done
# echo "SOURCE is '$SOURCE'"
# RDIR="$( dirname "$SOURCE" )"
# DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
# if [ "$DIR" != "$RDIR" ]; then
#   echo "DIR '$RDIR' resolves to '$DIR'"
# fi
# echo "DIR is '$DIR'"
