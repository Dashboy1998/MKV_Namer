#!/bin/bash

csv_file="compare_srt_renaming_history.csv"

while IFS=',' read -r origial_name predicted_name percentage_match; do
    mv "$predicted_name" "$origial_name"
done < "$csv_file"
