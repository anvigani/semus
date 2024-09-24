
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 92 mm) (* 35 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c'' { 
\cadenzaOn 
\omit Staff.TimeSignature 
\hide Staff.Stem
  
a1^"2" g^"0"^"|"-\tweak self-alignment-X #0 ^"nota perno" 
e^"-3" gs^"1" b^"4" c^"5" bf^"3" 
}