# Loops & Conditionals

## The for loop

* Go has **one** loop keyword → `for` → no `while`, no `do-while`
* Every loop does three jobs → **start** once, **check** before each round, **update** after each round

```go
sum := 0
for i := 0; i < 10; i++ {
	sum += i
}
fmt.Println(sum)   // 45 → 0+1+…+9
```

| Part | Go name | Here | Runs |
|---|---|---|---|
| start | init statement | `i := 0` | once, before the first round |
| check | condition | `i < 10` | before **every** round → `false` stops the loop |
| update | post statement | `i++` | at the end of every round |

* No `( )` around the header → `for (i := 0; i < 10; i++)` is a syntax error
* Braces `{ }` are **always** required, even for one line
* `i` declared in the init exists **only inside the loop** → using it after `}` → `undefined: i`
* `i++` is a statement, not an expression → `x := i++` is an error, `++i` doesn't exist

### Init and post are optional

```go
sum := 1                // start → done before the loop
for ; sum < 1000; {     // only the check is left in the header
	sum += sum          // update → done inside the body
}
fmt.Println(sum)        // 1024
```

* The jobs still happen, just outside the header → the `;` mark the empty slots
* The check runs **before** each round → the value can overshoot (1024, not 1000)
* Nothing updates the checked variable → infinite loop

### for as while

```go
sum := 1
for sum < 1000 {        // no semicolons → Go's "while"
	sum += sum
}
```

* Only a condition left → drop the `;` → `gofmt` does this for you
* C/Java `while (x < 5)` = Bash `while [ $x -lt 5 ]` = Go `for x < 5`

### Forever

```go
for {
	// runs until break, return or the program is killed
}
```

* No condition → loops forever → the Go playground kills it with `timeout running program`, locally stop it with `Ctrl+C`
* Used by programs meant to keep running → servers, agents polling every N seconds, Kubernetes controllers' reconcile loops (Bash → `while true; do … done`)
* Exit from inside with `break` (leave the loop) or `return` (leave the function)

```go
count := 0
for {
	count++
	if count == 3 {
		break
	}
}
```

### All forms side by side

```go
for i := 0; i < 5; i++ { }   // start + check + update
for ; i < 5; { }             // check only, gofmt removes the ;
for i < 5 { }                // while
for { }                      // forever
```

## if

```go
func sqrt(x float64) string {
	if x < 0 {
		return sqrt(-x) + "i"
	}
	return fmt.Sprint(math.Sqrt(x))
}

fmt.Println(sqrt(2), sqrt(-4))   // 1.4142135623730951 2i
```

* Same rules as `for` → no `( )` around the condition, braces required
* `return` inside the block leaves the function → the lines below don't run
* `sqrt` calling itself → recursion → safe here because `-x` is positive, so it stops after one extra call
* `fmt.Sprint(v)` → like `Println` but **returns** the text instead of printing it

### if with a short statement

```go
func pow(x, n, lim float64) float64 {
	if v := math.Pow(x, n); v < lim {
		return v
	}
	return lim
}

fmt.Println(pow(3, 2, 10), pow(3, 3, 20))   // 9 20
```

* `v := math.Pow(x, n)` runs once before the check → same idea as the init in `for`
* `v` exists **only inside the if** (and its `else`) → `return v` on the last line → `undefined: v`
* Declaring it on its own line also works → then `v` lives until the end of the function:

```go
v := math.Pow(x, n)
if v < lim {
	return v
}
return v   // fine, v is still in scope
```

| Declare the variable… | when |
|---|---|
| on its own line | you need it **after** the `if` |
| in the short statement | you only need it for the check and inside the block → can't be misused later, name can be reused |

* The most common real use → error checks that keep `err` scoped to one `if`:

```go
if err := step1(); err != nil { return err }
if err := step2(); err != nil { return err }   // a fresh err each time
```

### if and else

```go
func pow(x, n, lim float64) float64 {
	if v := math.Pow(x, n); v < lim {
		return v
	} else {
		fmt.Printf("%g >= %g\n", v, lim)
	}
	// v doesn't exist here
	return lim
}

fmt.Println(pow(3, 2, 10), pow(3, 3, 20))
// 27 >= 20
// 9 20
```

* Only one of the two blocks runs
* Short-statement variables are visible in `if` **and** `else`, gone after the final `}`
* `} else {` must be on **one line** → `else` on its own line is a syntax error
* Output order → **arguments are computed before the call starts** → both `pow` calls finish (the second one prints `27 >= 20`) before `Println` prints `9 20`
* `%g` → float in its shortest form → `27`, not `27.000000`

## switch

```go
switch os := runtime.GOOS; os {
case "darwin":
	fmt.Println("macOS.")
case "linux":
	fmt.Println("Linux.")
default:
	fmt.Printf("%s.\n", os)
}
```

* Shorter way to write a chain of `if / else if` on the same value
* `runtime.GOOS` → the OS the program runs on → `"linux"`, `"darwin"` (macOS), `"windows"`
* Optional short statement before the value, same scope rule as `if` → `os` lives only inside the switch
* `default` → runs when no case matches → like the final `else` (Bash → `*)`)
* Runs **only the matching case** → no `break` needed, no accidental fall-through like C/Java
* Want fall-through on purpose → `fallthrough` keyword (rare)
* Cases don't have to be constants or integers → strings, variables, function calls all work

### Evaluation order

```go
func f() int {
	fmt.Println("f was called!")
	return 1
}

switch i {
case 0:
	fmt.Println("matched 0")
case f():
	fmt.Println("matched f")
}
```

* Cases are checked **top to bottom**, the first match wins, the rest are **never evaluated**
* To check `case f():` Go must **call** `f` to know its value

| `i` | Output | Why |
|---|---|---|
| `0` | `matched 0` | first case matches → `f` never called |
| `1` | `f was called!` → `matched f` | `f` called to get `1` → `1 == 1` |
| `2` | `f was called!` | `f` called → `2 != 1` → nothing matches |

* Cases can be calculations, and the switch value can be a constant:

```go
today := time.Now().Weekday()   // Sunday = 0 … Saturday = 6
switch time.Saturday {
case today + 0:
	fmt.Println("Today.")
case today + 1:
	fmt.Println("Tomorrow.")
case today + 2:
	fmt.Println("In two days.")
default:
	fmt.Println("Too far away.")
}
```

* The Go playground's clock is fixed at 2009-11-10 23:00:00 UTC → Go's public release date → a Tuesday → prints `Too far away.`

### switch with no condition

```go
t := time.Now()
switch {
case t.Hour() < 12:
	fmt.Println("Good morning!")
case t.Hour() < 17:
	fmt.Println("Good afternoon.")
default:
	fmt.Println("Good evening.")
}
```

* Nothing after `switch` = `switch true` → each case is its own true/false check → first true case runs
* Clean replacement for long `if / else if / else` chains
* **Order matters** → at 9 AM both `< 12` and `< 17` are true → first one wins → most specific check goes first
* `< 17` doesn't need "and ≥ 12" → earlier cases already caught smaller values

## Exercise: square root with a loop

* Find √x without `math.Sqrt` → **guess, measure how wrong, improve, repeat**
* Improve step (Newton's method) → `z -= (z*z - x) / (2*z)`
    * `z*z - x` → how far the guess is from the target
    * `/ (2*z)` → scales the correction to how fast `z*z` changes
* Same thing in plain terms → `z = (z + x/z) / 2` → if `z` is too big, `x/z` is too small → the answer is between them → take the average

| Round | z | x / z | New z (x = 25) |
|---|---|---|---|
| 1 | 1 | 25 | 13 |
| 2 | 13 | 1.92 | 7.46 |
| 3 | 7.46 | 3.35 | 5.41 |
| 4 | 5.41 | 4.62 | 5.015 |
| 5 | 5.015 | 4.985 | 5.00002 |

```go
func Sqrt(x float64) float64 {
	z := 1.0                     // 1.0, not 1 → z must be float64
	for i := 0; i < 10; i++ {
		z -= (z*z - x) / (2 * z)
		fmt.Println(z)
	}
	return z
}
```

* Stop when the guess stops changing instead of a fixed 10 rounds:

```go
func Sqrt(x float64) float64 {
	z := 1.0
	for {
		next := z - (z*z-x)/(2*z)
		if math.Abs(next-z) < 1e-10 {
			return next
		}
		z = next
	}
}
```

* `math.Abs` → distance without the sign | `1e-10` → 0.0000000001
* Converges in a handful of rounds → result matches `math.Sqrt` to many decimal places
* Pattern worth knowing → **loop that improves a value until it's good enough** → same shape as retry loops and reconcile loops

| Symptom | Cause | Fix |
|---|---|---|
| `syntax error: unexpected :=, expected )` | C-style header `for (i := 0; …)` | remove the `( )` |
| `syntax error: unexpected name fmt, expected {` | `if x < 2 fmt.Println()` → missing braces | always use `{ }` |
| `undefined: i` after a loop | `i` lives only inside the `for` | declare it before the loop if needed after |
| `undefined: v` after an `if` | short-statement variable is scoped to `if`/`else` | declare it on its own line |
| `syntax error: unexpected keyword else, expected }` | `else` on a new line after `}` | write `} else {` |
| `timeout running program` / program never ends | condition never becomes false, or `for { }` without `break` | make sure the body changes what the check reads |
| `missing return` | a path through the function returns nothing | return on every path |
| Wrong switch case runs | a broader case sits above a narrower one | put the most specific case first |
| Side effect in a case runs unexpectedly | Go evaluated that case while searching | earlier cases didn't match → it had to be checked |
| `Printf` output runs into the next line | no `\n` | end the format with `\n` |

!!! tip "Quick revision"

    * `for` is the only loop → full form, `for cond {}` (while), `for {}` (forever)
    * No `( )` around `for`/`if`/`switch` headers, `{ }` always required
    * Short statement `if v := f(); v < x {}` → `v` lives in `if` + `else` only
    * `} else {` on one line
    * `switch` runs only the matching case, no `break` needed, cases can be any expression
    * Cases checked top to bottom, stops at first match, later cases never evaluated
    * `switch {}` with no value → each case is a condition → cleaner if-else chain

!!! question "Interview points"

    * How many loop keywords does Go have? → one, for; while and infinite loops are written with for
    * How do you write a while loop in Go? → for condition { }
    * Where is a variable declared in a for init statement visible? → only inside that for statement
    * What is an if short statement? → a statement before the condition, like if v := f(); v < 10, whose variables exist only in the if and its else
    * Why use the if short statement for err? → it keeps err scoped to one check so it can't leak or clash with later errors
    * How does Go's switch differ from C's? → only the matching case runs with no break needed, and cases need not be constants or integers
    * What does fallthrough do? → forces execution to continue into the next case
    * In what order are switch cases evaluated? → top to bottom, stopping at the first match; later cases are not evaluated
    * What is a switch with no condition? → the same as switch true; each case is a boolean expression, used to replace long if-else chains
    * Are function arguments evaluated before the call? → yes, all arguments are fully computed before the function body runs
