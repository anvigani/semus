
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 120 mm) (* 35 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' {
  
  \override Score.MetronomeMark.padding = 3
                             \tempo 4 = 60        % Tempi
  \time 2/4
c4 e d8 g a4
\time 3/4
g2 f4
\time 4/4
\tuplet 3/2 {e8 f g} d2 e4
c1
}