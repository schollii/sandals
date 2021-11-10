convu() {
  conv=$( units -f ~/.units.bytes $2 $3 | grep / | cut -f 2 -d " " )
  # sometimes the conversion factor is a large number output by
  # units in scientific notation so need to convert it to int with printf
  echo $(( $1 / $( printf "%.f" $conv ) ))
}
