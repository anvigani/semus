
\version "2.20.0"       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 150 mm) (* 28 mm))) paper-alist))     
\paper {#(set-paper-size "mio formato") top-margin = 4 left-margin = 0}  
\header {tagline = ""}

\relative c' { 
\cadenzaOn 
\omit Staff.TimeSignature 
\hide Staff.Stem
\clef bass
s1_"(Hz)"^"(n°)"
c,,1_"66"^"1"
c'_"132"^"2" 
g'_"196"^"3"
\clef treble
c_"264"^"4" 
e_"330"^"5" 
g_"396"^"6" 
bf_"462"^"7" 
c_"528"^"8" 
d_"594"^"9" 
e_"660"^"10" 
s_"..."^"..." 
}