<script lang="ts">
    import {type Server, serverList, userStore} from "$lib/userStore";
    import {ROOT} from "$lib/backend_location";
    import {onMount} from "svelte";
    import {goto} from "$app/navigation";

    /** @type {import('./$types').PageData} */
	export let data;

    let server_name_input: HTMLInputElement;
    let server_desc_input: HTMLInputElement;
    let invite_code_input: HTMLInputElement;

    let invite_code: string = "";

    let error_message: string | null = null;

    let server: Server | null = null;
    serverList.subscribe(s => {
        if (s == null) return;
        server = s.find(s => s.id == data!.id) ?? null;
    });

    onMount(() => {
        if (!$userStore || !serverList || serverList.length === 0) {
            goto("/");
        }
    });

    async function patch() {
        const new_name = server_name_input.value;
        const new_desc = server_desc_input.value;

        const res = await fetch(ROOT + "/v1/server", {
            method: "PATCH",
            headers: {
                Authorization: $userStore!.token,
            },
            body: JSON.stringify({
                id: server!.id,
                name: new_name,
                description: new_desc,
            }),
        });

        const json = await res.json();
        if (!res.ok) {
            error_message = json.error;
            return;
        }

        server!.name = new_name;
        server!.description = new_desc;
    }

    async function del() {
        const res = await fetch(ROOT + "/v1/server", {
            method: "DELETE",
            headers: {
                Authorization: $userStore!.token,
            },
            body: JSON.stringify({
                id: server!.id,
            }),
        });

        const json = await res.json();
        if (!res.ok) {
            error_message = json.error;
            return;
        }

        serverList.update(s => s!.filter(s => s.id != server!.id));
        await goto("/");
    }

    async function invite() {
        const res = await fetch(ROOT + "/v1/invite", {
            method: "POST",
            headers: {
                Authorization: $userStore!.token,
            },
            body: JSON.stringify({
                server: server!.id,
            }),
        });

        const json = await res.json();
        if (!res.ok) {
            error_message = json.error;
            return;
        }

        invite_code = json.code;
    }
</script>

<style>
    .content {
        max-width: 72ch;
        margin-inline: auto;
    }

    form {
        display: grid;
        gap: 1em;
    }

    label {
        display: grid;
        gap: 0.1em;
    }

    .buttons {
        display: grid;
        grid-auto-flow: column;
        gap: 1em;
        padding-top: 1.25em;
    }

    .invite {
        display: grid;
        grid-auto-columns: 2fr 1fr;
        grid-auto-flow: column;
        gap: 1em;
    }
</style>

<div class="content">
    <p>
        <a href="/chat/{server?.id}" class="deemphasis">« go back</a>
    </p>

    {#if error_message}
        <p class="toast">{error_message}</p>
    {/if}

    <form>
        <label for="server-name-input">
            Name
            <input
                    type="text"
                    id="server-name-input"
                    value={server?.name}
                    bind:this={server_name_input}
            >
        </label>

        <label for="server-description-input">
            Description
            <input
                    type="text"
                    id="server-description-input"
                    value={server?.description}
                    bind:this={server_desc_input}
            >
        </label>

        <div class="buttons">
            <button on:click={patch}>Apply Changes</button>
            <button on:click={del}>Delete {server?.name}</button>
        </div>

        <div class="invite">
            <button on:click={invite}>Create new invite code</button>
            {#if invite_code}
                <input
                        type="text"
                        id="invite-code-input"
                        readonly
                        bind:value={invite_code}
                        bind:this={invite_code_input}
                >
            {/if}
        </div>
    </form>
</div>
