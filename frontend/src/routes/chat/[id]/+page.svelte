<script lang="ts">
    import {userStore} from "$lib/userStore";
    import {ROOT} from "$lib/backend_location";
    import {onMount} from "svelte";
    import {goto} from "$app/navigation";

    /** @type {import('./$types').PageData} */
	export let data;

    let error_message: string | null = null;
    let message_input: HTMLInputElement;
    let send_button: HTMLButtonElement;
    let load_more_available: boolean = true;

    interface Message {
        id: number;
        author: number;
        content: string;
        created_at: string;
        server: number;
        username: string;
    }

    let messages: Array<Message> | null = null;

    onMount(() => {
        if (!$userStore) {
            goto("/");
        }
        loadMore();
    });

    let loaded_messages = 0;

    async function loadMore() {
        const limit = 100;

        const res = await fetch(ROOT + "/v1/message?" + new URLSearchParams({
            server: data!.id,
            limit: limit.toString(),
            offset: loaded_messages.toString(),
        }), {
            headers: {
                Authorization: $userStore!.token,
            }
        });

        if (!res.ok) {
            return;
        }

        const json: {messages: Array<Message>} = await res.json();
        loaded_messages += json.messages.length;

        if (messages != null)
            messages = [...messages, ...json.messages];
        else
            messages = json.messages;

        if (json.messages.length < limit) {
            load_more_available = false;
        }
    }

    async function send() {
        if (messages == null) return;

        send_button.disabled = true;
        message_input.disabled = true;

        const res = await fetch(ROOT + "/v1/message", {
            method: "POST",
            headers: {
                Authorization: $userStore!.token,
            },
            body: JSON.stringify({
                server: data!.id,
                content: message_input.value,
            })
        });

        const json = await res.json();

        if (!res.ok) {
            error_message = json.error;
            return;
        }

        json.username = $userStore!.username;

        messages = [json, ...messages];

        send_button.disabled = false;
        message_input.disabled = false;
        message_input.value = "";
        message_input.focus();
    }
</script>

<style>
    .content {
        max-width: 72ch;
        margin-inline: auto;
    }

    .controls {
        display: flex;
        flex-direction: row;
        gap: 0.25em;
    }

    .controls input[type=text] {
        flex-grow: 1;
    }

    .controls button {
        flex-shrink: 1;
    }

    .messages {
        display: grid;

        padding: 0;
        list-style: none;
    }

    .message:hover {
        background: rgba(255, 255, 255, 0.1);
    }

    .message .author::after {
        content: ":";
    }
</style>

<div class="content">
    <p>
        <a href="/" class="deemphasis">« go back</a>
    </p>

    {#if error_message}
        <p class="toast">{error_message}</p>
    {/if}

    {#if messages == null}
        <p>Loading...</p>
    {:else}
        <div class="controls">
            <input
                    type="text"
                    placeholder="Message chat"
                    bind:this={message_input}
            >
            <button
                    on:click={send}
                    bind:this={send_button}
            >Send</button>
        </div>

        <ul class="messages">
            {#each messages as message}
                <li class="message">
                    <span class="deemphasis author">{message.username}</span>
                    <span>{message.content}</span>
                </li>
            {/each}
        </ul>

        {#if load_more_available}
            <button on:click={loadMore}>load more messages</button>
        {:else}
            <p>...and you've reached the start of the conversation!</p>
        {/if}
    {/if}
</div>
