
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 92 mm) (* 25 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\cadenzaOn 
\omit Staff.TimeSignature 
\hide Staff.Stem
  
c1^"262" d^"294" e^"330" f^"349" g^"392" a^"440" b^"494" 
}