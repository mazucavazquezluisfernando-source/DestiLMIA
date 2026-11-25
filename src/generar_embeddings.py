def dividir_texto(texto, tokenizer, limite):
    ids = tokenizer.encode(texto, add_special_tokens=False, truncation=False)

    especiales = tokenizer.num_special_tokens_to_add(pair=False)
    tam = limite - especiales - 8

    if tam <= 0:
        raise ValueError("El tamaño del fragmento debe ser positivo.")

    fragmentos = []

    for inicio in range(0, len(ids), tam):
        fragmento = tokenizer.decode(
            ids[inicio:inicio + tam], skip_special_tokens=True
        )

        longitud = len(tokenizer.encode(
            fragmento, add_special_tokens=True, truncation=False
        ))

        if longitud > limite:
            raise ValueError("Un fragmento supera el límite del modelo.")

        fragmentos.append(fragmento)

    return fragmentos
