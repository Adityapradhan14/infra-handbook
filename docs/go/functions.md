# Functions & Printing

## Printing with fmt

```go
fmt.Println("My favorite number is", rand.Intn(10))
fmt.Printf("Now you have %g problems.\n", math.Sqrt(7))
```

* `fmt.Println(a, b)` → prints values, adds a **space between** them and a **newline** at the end
* `fmt.Printf("format", a, b)` → you write the line with placeholders (verbs) → nothing is added for you → end with `\n`
* `rand.Intn(10)` → random int from 0 to 9 (10 excluded)

| Verb | Prints | Example |
|---|---|---|
| `%v` | any value, default format | `42`, `true`, `hello` |
| `%d` | integer | `42` |
| `%s` | string | `hello` |
| `%q` | string in double quotes → makes empty strings and spaces visible | `"hello"`, `""` |
| `%g` | float, compact (no trailing zeros) | `2.6457513110645907` |
| `%.2f` | float, 2 decimal places | `2.65` |
| `%T` | the **type** of the value | `float64` |

* `%T` is the quickest way to check what type Go picked for a variable

## Standard library packages used here

* `fmt` → printing and formatting
* `math` → `math.Sqrt`, `math.Pow`, `math.Pi`
* `math/rand` → random numbers → used as `rand.Intn`, not `math.rand`
* `math/rand` is a **separate package** that lives in a subfolder of `math/` → importing `"math"` does not give you `rand`
* Name used in code = last element of the import path → `"net/http"` → `http`, `"encoding/json"` → `json`
* Full list → [pkg.go.dev/std](https://pkg.go.dev/std)

## Declaring a function

```go
func add(x int, y int) int {
	return x + y
}
```

* `func` → keyword | `add` → name | `(x int, y int)` → parameters | `int` after `)` → return type
* Type comes **after** the name → `x int` reads "x is an int" (C/Java write `int x`)
* Declared return type → every path must `return` a value of that type, or it doesn't compile
* Wrong argument type or count → compile error → `add(10)` → `not enough arguments in call to add`
* Short functions can sit on one line → `func needInt(x int) int { return x*10 + 1 }`

### Shared parameter types

```go
func add(x, y int) int           // x and y are both int
func h(a, b int, s string)       // a, b int → s string
func k(a int, s string, b int)   // a and b not consecutive → each needs its type
```

* A type covers every name to its **left** back to the previous type
* `func add(x, y) int` → error `undefined: x` → without a type Go reads `x` and `y` as type names → each group needs a type

## Multiple return values

```go
func swap(x, y string) (string, string) {
	return y, x
}

a, b := swap("hello", "world")   // a = "world", b = "hello"
```

* More than one return type → wrap them in `( )`
* Values are received **by position**
* Unwanted value → blank identifier `_` → `a, _ := swap("hello", "world")` → needed because unused variables are errors

### The (value, error) pattern

```go
f, err := os.Open("config.yaml")
if err != nil {
	fmt.Println("failed:", err)
	return
}
```

* Go has no exceptions → functions that can fail return the result **plus** an `error`
* `err` is `nil` when nothing went wrong → check it right after the call
* Same shape everywhere → `strconv.Atoi`, `os.ReadFile`, HTTP calls, Kubernetes client calls

## Named return values

```go
func split(sum int) (x, y int) {
	x = sum * 4 / 9   // 17*4/9 = 68/9 = 7 (integer division drops .55)
	y = sum - x       // 10
	return            // naked return → sends back x, y
}
```

* Named results are **created at the start** of the function with their zero values (`0`, `""`, `false`)
* Assign with `=`, not `:=` → they already exist
* Bare `return` (naked return) → returns the current values of the named results
* Same as writing `(int, int)` + `x := ...` + `return x, y` → just shorter
* Use naked return only in **short** functions → in long ones the reader can't see what's returned
* Names also document the result → `(prefix string)` says what comes back

```go
func greetingPrefix(language string) (prefix string) {
	switch language {
	case "French":
		prefix = "Bonjour, "
	default:
		prefix = "Hello, "
	}
	return
}
```

| Symptom | Cause | Fix |
|---|---|---|
| `not enough arguments in call to add` | fewer arguments than parameters | pass every parameter |
| `cannot use "13" (untyped string constant) as int value` | argument of the wrong type | pass the declared type, or convert it |
| `missing return` | a path through the function returns nothing | return a value on every path |
| `undefined: x` on a function's own parameter line | `func add(x, y) int` → no type, so Go reads `x` and `y` as type names | give the group a type → `x, y int` |
| `declared and not used: b` | received a return value you don't use | replace it with `_` |
| `assignment mismatch: 1 variable but swap returns 2 values` | caught only one of several results | receive all of them, `_` for the unwanted ones |
| Printf output runs into the next line | `Printf` adds no newline | end the format with `\n` |

!!! tip "Quick revision"

    * `func name(a, b int) (int, error) { ... }` → type after name, shared types, results in `( )`
    * `Println` = spaces + newline | `Printf` = verbs, add `\n` yourself
    * `%v` any | `%d` int | `%s` string | `%q` quoted | `%T` type
    * `_` throws away a value | `err != nil` → something failed
    * Named results start at zero values, naked `return` only in short functions

!!! question "Interview points"

    * How does Go handle errors without exceptions? → functions return an error as their last value and the caller checks if err != nil
    * What is the blank identifier? → _ , used to discard a value you must receive but don't need
    * What are named return values? → result parameters declared with names; they start at zero values and a bare return sends them back
    * When should you avoid naked returns? → in long functions, because the reader can't tell what is being returned
    * Println vs Printf? → Println prints values separated by spaces with a newline; Printf uses a format string with verbs and adds nothing
    * Why use %q in test failure messages? → it quotes strings, so empty strings and stray spaces become visible
    * How do you find a value's type at runtime while debugging? → fmt.Printf("%T", v)
    * Is math/rand part of the math package? → no, it is a separate package stored under the math/ directory
