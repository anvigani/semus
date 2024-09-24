
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 120 mm) (* 35 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' {
  
  \override Score.MetronomeMark.padding = 3
                             \tempo 4. = 60        % Tempi
  \time 3/8
c4 e8 d8 g a
\time 6/8
g4 f8 e f g
\time 9/8
\tuplet 2/3 {d8 e} c4. g'4.
}