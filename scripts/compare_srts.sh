#!/bin/bash

sub_a="$1"
sub_b="$2"

different_lines=$( sdiff -B -b -s -i "$sub_a" "$sub_b" | wc -l )
echo "$different_lines"
