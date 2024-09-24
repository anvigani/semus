\version "2.20.0"                       
\language "english" 

#(set! paper-alist (cons '("mio formato" . (cons (* 35 mm) (* 90 mm))) paper-alist) )  
\paper {#(set-paper-size "mio formato") top-margin = 3 left-margin = 7} 
\layout{#(layout-set-staff-size 20) indent = 0 short-indent = 0}
\header {tagline = ""}

                 \new Staff  {\time 9/8   \omit Staff.TimeSignature 
\hide Staff.Stem

\arpeggioBracket
 < c' fs' d'' g''>1  \arpeggio s8}
\new StaffGroup <<\time 9/8 

                 \new Staff  {  \omit Staff.TimeSignature 
\hide Staff.Stem s8 g''1\p}
                 \new Staff  {  \omit Staff.TimeSignature 
\hide Staff.Stem s8 d''1\mf}
                 \new Staff  {  \omit Staff.TimeSignature 
\hide Staff.Stem s8 fs'1\pp}
                 \new Staff  {  \omit Staff.TimeSignature 
\hide Staff.Stem s8  c'1\f}
>>