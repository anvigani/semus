
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 92 mm) (* 25 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\cadenzaOn 
\omit Staff.TimeSignature 
\hide Staff.Stem
  
c1^"60" cs^"61" d^"62" e^"64" f^"65" g^"67" a^"69" b^"71"
}