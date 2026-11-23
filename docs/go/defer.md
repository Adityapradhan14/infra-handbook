# Defer

## What defer does

```go
func main() {
	defer fmt.Println("world")
	fmt.Println("hello")
}
// hello
// world
```

* `defer` → **don't run this now, run it right before the surrounding function returns**
* Written first, runs last → the call is saved on a list, executed when the function ends
* Runs however the function exits → reaching `}`, any `return`, or a panic

## Why it exists → cleanup

```go
func readConfig(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()   // written right next to Open → can't be forgotten

	// … read the file, maybe return early in several places …
	return nil
}   // f.Close() runs here, on every exit path
```

* Without `defer` → `Close()` must be repeated before **every** `return` → miss one and the file leaks
* With `defer` → write it once, right after acquiring the resource
* Typical uses → closing files, HTTP response bodies, DB connections, unlocking a mutex, removing temp files
* Bash equivalent → `trap 'rm -f /tmp/lockfile' EXIT`

## Arguments are evaluated immediately

```go
x := 1
defer fmt.Println("deferred x =", x)   // x is captured as 1 here
x = 100
fmt.Println("current x =", x)
// current x = 100
// deferred x = 1
```

* The **values** are fixed when the `defer` line runs → only the **call** is delayed
* Like a photo → snapshot taken at the `defer` line, printed at the end
* Changing the variable later doesn't change what was saved

## Stacking defers

```go
fmt.Println("counting")
for i := 0; i < 10; i++ {
	defer fmt.Println(i)
}
fmt.Println("done")
// counting
// done
// 9
// 8
// …
// 0
```

* Deferred calls go onto a **stack** → run in **LIFO** order → last in, first out
* Pile of plates → 0 goes in first, 9 lands on top → 9 comes off first
* Each `defer fmt.Println(i)` captured the `i` of its own round → 0…9, not ten 10s
* Reverse order matches cleanup → release things in the opposite order you acquired them:

```go
db := connectDB()
defer db.Close()     // deferred 1st → runs last

f := openFile()
defer f.Close()      // deferred 2nd → runs first
```

```go
defer fmt.Println("A")
defer fmt.Println("B")
fmt.Println("C")
defer fmt.Println("D")
// C
// D
// B
// A
```

| Symptom | Cause | Fix |
|---|---|---|
| Deferred call prints an old value | arguments captured when `defer` ran | defer after the value is final, or defer a closure that reads it at the end |
| Deferred calls run in the "wrong" order | defers are LIFO | order the `defer` lines in reverse of the order you want them to run |
| Files or connections pile up in a long loop | `defer` inside a loop only runs when the **function** returns | move the loop body into its own function, or close explicitly each round |
| `defer f.Close()` panics on a nil `f` | deferred before checking `err` | check `err` first, then `defer` |

!!! tip "Quick revision"

    * `defer f()` → runs `f` just before the surrounding function returns
    * Arguments evaluated at the `defer` line, call delayed
    * Several defers → LIFO → last deferred runs first
    * Put `defer x.Close()` right after a successful open
    * `defer` in a loop waits for the function, not the loop round

!!! question "Interview points"

    * When does a deferred call run? → just before the surrounding function returns, on every exit path including panics
    * When are a deferred call's arguments evaluated? → immediately, when the defer statement executes; only the call is delayed
    * In what order do multiple defers run? → last in, first out, like a stack
    * Why is LIFO the right order for defers? → resources are released in reverse of how they were acquired
    * What is the classic use of defer? → cleanup such as closing files and response bodies or unlocking mutexes
    * Why is defer inside a long loop risky? → deferred calls pile up until the function returns, holding resources open
    * Why check err before deferring Close? → if the open failed the value may be nil and the deferred Close would fail or panic
