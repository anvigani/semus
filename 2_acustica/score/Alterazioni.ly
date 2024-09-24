
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 92 mm) (* 25 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\omit Staff.TimeSignature 
\hide Staff.Stem
\hide Staff.BarLine
\time 7/1
g'!1 gs gss s a! af aff 
}