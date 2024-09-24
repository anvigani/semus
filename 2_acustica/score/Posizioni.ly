
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 110 mm) (* 25 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\omit Staff.TimeSignature 
\hide Staff.Stem
\hide Staff.BarLine
\time 5/1
e1^"mi" g^"sol" b^"si" d^"re" f^"fa" s
 f,^"fa" a^"la" c^"do" e^"mi"  
}