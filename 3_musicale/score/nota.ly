
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 30 mm) (* 25 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\cadenzaOn 
\omit Staff.TimeSignature 
  
g'8 s
}