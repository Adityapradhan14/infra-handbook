# Variables, Types & Constants

## Declaring variables with var

```go
var c, python, java bool   // package level → visible to every function in the package

func main() {
	var i int              // function level → only inside main
	fmt.Println(i, c, python, java)   // 0 false false false
}
```

* `var name type` → type after the name, one type covers the whole list
* Group several declarations in a block, like grouped imports:

```go
var (
	ToBe   bool   = false
	MaxInt uint64 = 1<<64 - 1
)
```

* Unused **local** variable → compile error `declared and not used: z`
* Unused **package-level** variable → allowed

## Zero values

* A variable declared without a value gets its type's **zero value** → never garbage, never "undefined"

| Type | Zero value |
|---|---|
| `int`, `float64` | `0` |
| `bool` | `false` |
| `string` | `""` → a string with no characters |
| pointers, slices, maps, errors | `nil` → "points to nothing" |

```go
var s string
fmt.Println(len(s))          // 0
fmt.Printf("%q\n", s)        // ""
fmt.Println(1, s, s, s)      // "1   " → empty strings print as nothing, only the spaces remain
```

* Empty strings are invisible with `Println` / `%v` → use `%q` to see them
* `if err != nil` works because an error that was never set is `nil`

## Initializers and type inference

```go
var i, j int = 1, 2                           // type given → values must match it
var c, python, java = true, 4.359, "no!"      // no type → Go infers bool, float64, string
```

* Values are matched **by position** → count must match the names
* Need at least a type **or** a value → `var x` alone is a syntax error
* When the type is left out, Go takes it from the right side:
    * another variable → same type as that variable → `var i int; j := i` → `j` is `int`
    * a literal → from how it looks

| Literal | Inferred type |
|---|---|
| `42` | `int` |
| `42.0`, `3.142` | `float64` → the dot alone makes it a float |
| `"42"` | `string` → quotes make it text, even if it's digits |
| `true` | `bool` |
| `0.5i` | `complex128` |

## Short declaration :=

```go
k := 3                                    // same as var k = 3
c, python, java := true, false, "no!"
got := Hello()                            // the line from the first test
```

* `:=` → create + assign + infer the type, in one step
* **Only inside functions** → at package level it's `syntax error: non-declaration statement outside function body` → use `var`
* `:=` **creates**, `=` **changes**:

```go
k := 3     // create
k = 5      // change an existing variable
k := 7     // ❌ no new variables on left side of :=
```

* With several names, at least **one** must be new → `b, err := g()` after `a, err := f()` reuses `err`
* Style → `:=` inside functions by default | `var x int` when you mean "start at the zero value"

## Basic types

| Use for | Type |
|---|---|
| whole numbers | `int` → default choice |
| decimals | `float64` → default choice |
| text | `string` |
| true/false | `bool` |
| one raw byte (files, network data) | `byte` = alias for `uint8` |
| one character (Unicode code point) | `rune` = alias for `int32` |

* Sized variants exist for when a size is required (file formats, protocols): `int8`…`int64`, `uint`, `uint8`…`uint64`, `uintptr`, `float32`, `complex64`, `complex128`
* Number = bits → `int64` holds 64 bits | `u` = unsigned → no negatives
* `1<<64 - 1` → 2⁶⁴ − 1 = `18446744073709551615` → the largest `uint64`
* `int`, `uint`, `uintptr` → 64 bits on 64-bit systems, 32 bits on 32-bit systems
* Strings are UTF-8 → `"世界"` works as-is

## Integer division

```go
17 * 4 / 9   // 7, not 7.55
42 / 5       // 8, not 8.4
```

* `int ÷ int` → `int` → the decimal part is **dropped** (truncated toward zero, not rounded)
* Need decimals → make one side a float → `42.0 / 5` → `8.4`

## Type conversions

* Go **never converts types automatically** → you write `Type(value)`

```go
var x, y int = 3, 4
var f float64 = math.Sqrt(float64(x*x + y*y))   // Sqrt only accepts float64
var z uint = uint(f)
fmt.Println(x, y, z)                            // 3 4 5
```

* Read nested calls inside-out → `x*x + y*y` = `25` (int) → `float64(25)` → `Sqrt` → `5`
* Conversion makes a **new value** of the new type → the original variable keeps its type
* Mixing types in maths is an error → `a + b` with `int` and `float64` → `float64(a) + b`
* float **variable** → int truncates toward zero → `f := 7.9` → `int(f)` = `7`, `int(-f)` = `-7`
* float **constant** → int that loses the fraction is a compile error → `int(7.9)` → `cannot convert 7.9 (untyped float constant) to type int`
* Number → text is **not** `string(n)` → `string(rune(65))` is `"A"` (a character code) → use `strconv`:

```go
strconv.Itoa(65)       // "65"
n, err := strconv.Atoi("65")   // 65, nil → returns (value, error)
```

* Env vars and flags always arrive as strings → `strconv.Atoi` for ports, replica counts, timeouts

## Constants

```go
const Pi = 3.14

func main() {
	const World = "世界"
	const Truth = true
	fmt.Println("Hello", World)   // Hello 世界
}
```

* `const` → value fixed at compile time, can **never** change → `Pi = 3.15` → `cannot assign to Pi`
* Allowed kinds → character, string, boolean, numeric
* Package or function level, like `var`
* **No `:=`** → `const Pi := 3.14` → `syntax error: unexpected :=, expected =`
* Use for values that must not change → prefixes, default ports, fixed messages → a named constant reads better than a bare literal:

```go
const englishHelloPrefix = "Hello, "

func Hello(name string) string {
	return englishHelloPrefix + name
}
```

### Untyped numeric constants

```go
const (
	Big   = 1 << 100   // 1 followed by 100 binary zeros (~1.27e30)
	Small = Big >> 99  // 2
)

func needInt(x int) int           { return x*10 + 1 }
func needFloat(x float64) float64 { return x * 0.1 }

fmt.Println(needInt(Small))    // 21
fmt.Println(needFloat(Small))  // 0.2
fmt.Println(needFloat(Big))    // 1.2676506002282295e+29
fmt.Println(needInt(Big))      // ❌ overflows int
```

* A constant without a type has **no fixed type yet** → it takes the type its context needs
* Same `Small` goes into an `int` function and a `float64` function with no conversion → a typed variable couldn't do that
* Constants are kept at high precision → only checked when used
* Value doesn't fit the type it's used as → compile error instead of a silently wrong number
* `e+29` → scientific notation → ×10²⁹

| Symptom | Cause | Fix |
|---|---|---|
| `declared and not used: z` | local variable never used | use it, delete it, or assign to `_` |
| `no new variables on left side of :=` | `:=` on a name that already exists | use `=` to change it |
| `syntax error: non-declaration statement outside function body` | `:=` at package level | `var k = 3` |
| `syntax error: unexpected semicolon, expected type` | `var x` with no type and no value | give a type or a value |
| `cannot use x (variable of type int) as float64 value in argument to math.Sqrt` | no automatic conversion | `math.Sqrt(float64(x))` |
| `invalid operation: a + b (mismatched types int and float64)` | maths across types | convert one side |
| `cannot convert 7.9 (untyped float constant) to type int` | constant would lose its fraction | convert a variable, or use `math.Floor` / `math.Round` first |
| `cannot assign to Pi` | changing a constant | use `var` if it must change |
| `syntax error: unexpected :=, expected =` | `const x := ...` | `const x = ...` |
| `cannot use Big (untyped int constant ...) as int value ... (overflows)` | constant too large for the type | use a bigger type such as `float64` |
| Output shows nothing where a string should be | empty string `""` | print with `%q` |
| `string(65)` gives `"A"` | converts a code point, not digits | `strconv.Itoa(65)` |
| Division result is missing its decimals | `int / int` | make one operand a float |

!!! tip "Quick revision"

    * `var x int` → zero value | `var x = 5` → inferred | `x := 5` → inside functions only
    * Zero values: `0`, `false`, `""`, `nil`
    * `:=` creates, `=` changes
    * Default types: `int`, `float64`, `string`, `bool`
    * No automatic conversion → `float64(x)` | text ↔ number → `strconv`
    * `int / int` drops the decimals
    * `const` never changes, no `:=` | untyped constants adapt to their context

!!! question "Interview points"

    * What is a zero value in Go? → the value a variable gets when declared without one: 0, false, "" or nil depending on the type
    * Why does Go have zero values instead of undefined? → every variable always holds a valid, predictable value, so there is no uninitialized memory to read
    * var vs := ? → := declares and infers inside functions only; var works everywhere and can declare without a value
    * When does := fail on an existing name? → when no variable on the left side is new
    * How does type inference work for literals? → 42 becomes int, 4.2 float64, "x" string, true bool
    * Does Go convert int to float64 automatically? → no, conversions are always explicit with T(v)
    * What happens when converting a float variable to int? → the fraction is truncated toward zero
    * Why is string(65) not "65"? → it converts the number to the character with that code point; use strconv.Itoa for decimal text
    * What is an untyped constant? → a constant with no fixed type that takes the type required where it is used, kept at high precision until then
    * Can a constant be declared with := ? → no, constants use const name = value
    * What are byte and rune? → aliases for uint8 and int32, used for raw bytes and Unicode characters
