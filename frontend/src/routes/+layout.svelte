<script lang="ts">
    import { userStore } from '$lib/userStore';
    import "$lib/styles/main.scss";
    import {ROOT} from "$lib/backend_location";

    async function logout() {
        await fetch(ROOT + "/v1/auth/logout", {
            method: "POST"
        });

        userStore.set(null);
    }
</script>

<style lang="scss">
    :global(body) {
        margin: 0;
        min-height: 100vh;

        display: flex;
        flex-direction: column;
    }

    header {
        flex-shrink: 1;

        border-bottom: 1px solid gray;
        padding-block: 0.5em;
        padding-inline: 1em;

        display: flex;
        justify-content: end;
        align-items: end;
        gap: 0.75em;
    }

    .content {
        flex-grow: 1;
    }

    footer {
        flex-shrink: 1;

        border-top: 1px solid gray;
        padding-block: 0.5em 5em;
        padding-inline: 1em;

        text-align: center;
    }
</style>

<header>
    {#if $userStore}
        <span>
            <span class="deemphasis">Logged in as</span>
            {$userStore.username}
        </span>
        <button on:click={logout}>Logout</button>
    {:else}
        <a href="/login">Log in</a>
        <a href="/register">Register</a>
    {/if}
</header>

<div class="content">
    <slot />
</div>

<footer>
    <p class="deemphasis">&copy; 2024, Emre Özcan & A. Eren Aydoğdu.</p>
</footer>
