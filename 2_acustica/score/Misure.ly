
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 92 mm) (* 35 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' {
  
  \override Score.MetronomeMark.padding = 3
                             \tempo 4 = 60        % Tempi
  \time 5/4
c4 d e8 f g2
\time 3/4
a4 r4 \tuplet 3/2 {b8 a g} 
}