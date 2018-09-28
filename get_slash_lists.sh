#!/usr/bin/env bash

function set_env()
{
    cd $INFINIBOX_TESTS
    source $ENV_PATH
}

function slash_list_tests()
{

    set_env
    slash list tests --only-tests --show-tags
}


function slash_list_suite()
{
    set_env
    slash list -f $1 --no-params --only-tests

}

"$@"



