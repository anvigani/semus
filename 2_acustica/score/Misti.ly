
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 120 mm) (* 35 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\omit Staff.TimeSignature 
%\hide Staff.Stem
\hide Staff.BarLine
\override Score.MetronomeMark.padding = 3
                             \tempo 4 = 60        % Tempi
\time 4/4

c4 8 8
\tuplet 3/2 { c8 c c }
8 8
\tuplet 5/4 { 16 16 16 16 16  }
\tuplet 3/2 { c8 c c }
16 16 16 16
1
}