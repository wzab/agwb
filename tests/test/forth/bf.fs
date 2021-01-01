\ This file implements bitfield operations
\ It assumes, that we have the bus access
\ words:
\ wb@ ( address -- val )
\ wb! ( val address -- )
\ The bitfield is defined by the mask
\ (ones correspond to the bits used by the field)
\ and by the shift (position of the LSB in the cell)

: bf@ ( address mask shift -- val )
  rot ( mask shift address )
  wb@ ( mask shift val )
  rot ( shift val mask )
  and ( shift val )
  swap ( val shift )
  rshift ( val )
;

: bf! ( val address mask shift -- )
  rot ( val mask shift address )
  >r ( val mask shift ) ( R: address )
  rot (  mask shift val ) ( R: address )
  swap (  mask val shift ) ( R: address )
  lshift ( mask val ) ( R: address )
  over ( mask val mask ) ( R: address )
  and ( mask val ) ( R: address )
  swap invert ( val ^mask ) ( R: address )
  r@ ( val ^mask address )  ( R: address )
  wb@ ( val ^mask oldval ) ( R: address )
  and ( val oldval-masked) ( R: address )
  or ( val ) ( R: address )
  r> ( val address )
  wb!
;
