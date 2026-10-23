# Generics intro (eksempel)

*[Animasjon: `List<string>` og `List<int>` vises ved siden av hverandre.]*
Har dere lagt merke til at vi kan lage både en List<string> og en List<int>, uten at noen har skrevet to forskjellige listeklasser? I denne videoen skal vi se hvordan det er mulig.

*[Animasjon: Klassene skrives ut én etter én. Datatypene `string`, `int` og `Person` markeres med farge, resten av koden blir grå. Så glir de tre klassene sammen til én, og datatypene erstattes av `T`.]*
Se hva som skjer hvis vi prøver å lage en slik beholder uten generics:
```csharp
public class StringContainer { public string Value { get; set; } }
public class IntContainer    { public int Value { get; set; } }
public class PersonContainer { public Person Value { get; set; } }
```
Legg merke til at disse tre klassene er helt like, bortsett fra datatypen. Hvis vi vil endre en regel, må vi endre den tre steder. Dette burde gi en umiddelbar iffy code-smell.

For å hjelpe med dette har C# støtte for noe som heter Generics.
Når vi designer en klasse, som skal bestemme regler for tilgang til noe data, men vi vet ikke helt hva dataen er når vi designer klassen, har vi tilgang til et typeparameter i klassedefinisjonen vår.
Se på følgende:
```csharp
public class Container<T>
{
    public T Value {get;set;}
}
```

*[Animasjon: `Container<T>` vokser til fire linjer. `<T>` markeres, og så `T Value`, med «set: tar imot T» og «get: gir ut T».]*
Her har vi en super simpel container klasse, med et Value property. Legg merke til det litt sære <T>, dette representerer et typeparameter vi gir ut av klassen vår. Når vi faktisk lager et objekt som representerer denne klassen, må vi gi objektdeklarasjonen vår en type den skal faktisk jobbe med. Vi ser at klassen vår kan ta imot, og gi ut data av typen T.
