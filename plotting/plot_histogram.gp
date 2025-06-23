#!/usr/bin/gnuplot --persist

set terminal png
set size 1,1
set term png size 1400, 600
set output 'graph.png'

set datafile separator " "

set multiplot layout 2,1 rowsfirst

binwidth = 50
bin(x, width) = width*floor(x/width)
set tics out nomirror
set style fill transparent solid 0.5 border lt -1
set xrange [0:1200]
set xtics binwidth
set boxwidth binwidth
#set yrange [0:500000]
set grid
plot filename u (bin($1,binwidth)):(1.0) smooth freq with boxes notitle

binwidth = 20
bin(x, width) = width*floor(x/width)
set tics out nomirror
set style fill transparent solid 0.5 border lt -1
set xrange [250:1000]
set xtics binwidth
set boxwidth binwidth
set yrange [0:200000]
set grid
plot filename u (bin($1,binwidth)):(1.0) smooth freq with boxes notitle

unset multiplot
