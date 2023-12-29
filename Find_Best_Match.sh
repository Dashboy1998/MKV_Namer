#/bin/bash

# Downloaded Subs
# DVD Sub
#sub1="D1/B6_t05.mkv.srttxt2"
dvdsub="B6_t05.mkv.srttxt2"
results_file="results.csv"
# Remove time stamps and number lines
# find . -name "*.srt" -exec sh -c "tac  {} | sed '/[0-9][0-9]:[0-9][0-9]:[0-9][0-9].*/,+1d' | tac > {}txt" \;
# Remove Special Charactors

# Remove Spaces during each block



#sdiff -B -b -s -i "$dvdsub" "$sub1" | wc -l

number_of_lines=$( cat "$dvdsub" | wc -l)
# Print Headers
echo "MKVSRT,ORTSRT,MTOTAL,OTOTAL,DIFF,PERCENTAGE_DIFF" > "tmp_$results_file"
find . -mindepth 2 -name "*.srttxt2" -print0 | while read -d $'\0' file
do
    ort_number_of_lines=$( cat "$file" | wc -l)
    different_lines=$( sdiff -B -b -s -i "$dvdsub" "$file" | wc -l )
    #     MKVSRT, ORTSRT, MTOTAL,        OTOTAL,              DIFF             PERCENTAGE DIFF
    echo "$dvdsub,$file,$number_of_lines,$ort_number_of_lines,$different_lines,$(( 100 * different_lines / number_of_lines ))" >> "tmp_$results_file"
done

sort -k5 -n -t, "tmp_$results_file" > "$results_file"

best_match_Percentage=""
threshold_limit=25

while IFS="," read -r MKVSRT ORTSRT MTOTAL OTOTAL DIFF PERCENTAGE_DIFF
do

    echo "Best match is $ORTSRT at $(( PERCENTAGE_DIFF )) (Lower is better)"
    best_match=

done < <(tail -n +2 "$results_file")
#TODO
# Add threshold for difference (Maybe less than 25% difference)
# See if next best match is within X (Maybe 20%)
# Change from CSV to database
# Rename best match file
